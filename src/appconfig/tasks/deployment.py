# deployment.py

import os
import json
import time
import platform
import tempfile
import functools
import random
import pathlib
import re

from fabric.api import env, settings, shell_env, prompt, sudo, run, cd, local
from fabric.contrib.files import exists
from fabric.contrib.console import confirm
from fabtools import (
    require, files, python, postgres, nginx, system, service, supervisor, user)
from clldutils import misc

import appconfig
from .. import PKG_DIR
from .. import helpers
from .. import cdstar
from .. import systemd
from . import letsencrypt

from . import task_app_from_environment

__all__ = [
    'deploy', 'start', 'stop', 'uninstall', 'sudo_upload_template', 'upgrade',
    'upload_dump', 'download_backups',
]

PLATFORM = platform.system().lower()
TEMPLATE_DIR = PKG_DIR / 'templates'


def template_context(app, workers=3):
    ctx = {
        'PRODUCTION_HOST': env.host in appconfig.APPS.production_hosts,
        'app': app, 'env': env, 'workers': workers,
        'auth': '',
    }

    return ctx


def sudo_upload_template(template,
                         dest,
                         context=None,
                         mode=None,
                         user_own=None,
                         **kwargs):
    """
    A wrapper around upload_template in fabtools. Used to upload template files.

    :param user_own: Set to user name that's supposed to own the file.
        If it is None, the uploading user's rights are used.
    :type user_own: str

    :return: None
    """
    if kwargs:
        context = (context or {}).copy()
        context.update(kwargs)
    tdir = TEMPLATE_DIR
    if (
            context
            and ('app' in context)
            and TEMPLATE_DIR.joinpath(context['app'].name, template).exists()
    ):
        tdir = TEMPLATE_DIR / context['app'].name

    files.upload_template(
        template,
        dest,
        context,
        use_jinja=True,
        template_dir=str(tdir),
        use_sudo=True,
        backup=False,
        mode=mode,
        chown=True,
        user=user_own)


def pip_freeze(app, packages=None):
    with python.virtualenv(str(app.venv_dir)):
        stdout = run('pip freeze', combine_stderr=False)

    def iterlines(lines):
        for line in lines:
            if ('You are' in line) or ('You should' in line):
                continue
            if packages and line.partition('==')[0] in packages:
                print(line)
            yield line + '\n'

    target = appconfig.APPS_DIR / app.name / 'requirements.txt'
    with target.open('w', encoding='ascii') as fp:
        fp.writelines(iterlines(stdout.splitlines()))


def check(app):
    time.sleep(5)
    res = run('curl http://localhost:%s/_ping' % app.port)
    assert json.loads(res)['status'] == 'ok'

    if env.environment == 'production':
        if app.public:
            # Production apps are served over HTTPS. If they are public, we can
            # check the complete stack:
            res_https = run('curl https://%s/_ping' % (app.domain))
            assert json.loads(res_https)['status'] == 'ok'


@task_app_from_environment
def upgrade(app, **packages):
    """
    usage: fab upgrade:production,waitress=1.4.3
    """
    with python.virtualenv(str(app.venv_dir)):
        require.python.packages(
            ['{0}=={1}'.format(*pkg) for pkg in packages.items()], use_sudo=True)
    pip_freeze(app, packages)
    stop.execute_inner(app)
    start.execute_inner(app)
    check(app)


@task_app_from_environment
def start(app):  # only tested implicitly
    """start app by changing the supervisord config"""
    require_supervisor(app.supervisor, app)
    supervisor.update_config()
    service.reload('nginx')


@task_app_from_environment
def stop(app, maintenance_hours=1):  # only tested implictly
    """pause app by changing the supervisord config

    create a maintenance page giving a date when we expect the service will be back
    :param maintenance_hours: Number of hours we expect the downtime to last.
    """
    if maintenance_hours is not None:
        require.directory(str(app.www_dir), use_sudo=True)
        timestamp = helpers.strfnow(add_hours=maintenance_hours)
        sudo_upload_template('503.html', dest=str(app.www_dir / '503.html'),
                             app_name=app.name, timestamp=timestamp)

    require_supervisor(app.supervisor, app, pause=True)
    supervisor.update_config()
    service.reload('nginx')


def require_supervisor(filepath, app, pause=False):  # only tested implictly
    # TODO: consider require.supervisor.process
    sudo_upload_template('supervisor.conf',
                         dest=str(filepath),
                         mode='644',
                         PAUSE=pause,
                         app=app)


@task_app_from_environment
def uninstall(app):  # pragma: no cover
    """uninstall the app"""
    for path in (app.nginx_location, app.nginx_site, app.venv_dir):
        if exists(str(path)):
            if path == app.nginx_site:
                nginx.disable(app.nginx_site.name)
            files.remove(str(path), recursive=True, use_sudo=True)

    stop.execute_inner(app)
    if user.exists(app.name):
        sudo('dropdb --if-exists %s' % app.name, user='postgres')
        sudo('userdel -rf %s' % app.name)

    if exists(str(app.supervisor)):
        files.remove(str(app.supervisor), recursive=True, use_sudo=True)

    supervisor.update_config()
    service.reload('nginx')
    systemd.uninstall(app, pathlib.Path(os.getcwd()) / 'systemd')


@task_app_from_environment
def deploy(app, with_alembic=False):
    """deploy the app"""
    assert system.distrib_id() == 'Ubuntu'
    lsb_codename = system.distrib_codename()
    if lsb_codename not in ['xenial', 'bionic', 'focal']:
        raise ValueError('unsupported platform: %s' % lsb_codename)

    # See whether the local appconfig clone is up-to-date with the remote master:
    remote_repo = local(
        'git ls-remote git@github.com:dlce-eva/appconfig.git HEAD | awk \'{ print $1}\'',
        capture=True)
    local_clone = local('git rev-parse HEAD', capture=True)
    if remote_repo != local_clone:
        if confirm('Local appconfig clone is not up-to-date '
                   'with remote master, continue?', default=False):
            print("Continuing deployment.")
        else:
            print("Deployment aborted.")
            return

    require.deb.packages(getattr(app, 'require_deb_%s' % lsb_codename) + app.require_deb)
    require.users.user(app.name, create_home=True, shell='/bin/bash')
    require.directory(str(app.www_dir), use_sudo=True)
    require.directory(str(app.www_dir / 'files'), use_sudo=True)
    require_logging(app.log_dir,
                    logrotate=app.logrotate,
                    access_log=app.access_log, error_log=app.error_log)

    workers = 3 if app.workers > 3 and env.environment == 'test' else app.workers

    if env.environment != 'staging':
        # Test and production instances are publicly accessible over HTTPS.
        letsencrypt.require_certbot()
        letsencrypt.require_cert(env.host)
        if env.environment == 'production':
            letsencrypt.require_cert(app)

    ctx = template_context(app, workers=workers)

    #
    # Create a virtualenv for the app and install the app package in development
    # mode, i.e. with repository working copy in /usr/venvs/<APP>/src
    #
    require_venv(
        app.venv_dir,
        require_packages=[app.app_pkg] + app.require_pip,
        assets_name=app.name if app.stack == 'clld' else None)

    #
    # If some of the static assets are managed via bower, update them.
    #
    require_bower(app)
    require_grunt(app)

    require_nginx(ctx)
    require_postgres(app)

    require_config(app.config, app, ctx)

    # if gunicorn runs, make it gracefully reload the app by sending HUP
    # TODO: consider 'supervisorctl signal HUP $name' instead (xenial+)
    sudo('( [ -f {0} ] && kill -0 $(cat {0}) 2> /dev/null '
         '&& kill -HUP $(cat {0}) ) || echo no reload '.format(app.gunicorn_pid))

    if not with_alembic and confirm('Recreate database?', default=False):
        stop.execute_inner(app)
        upload_sqldump(app)
    elif (
            exists(str(app.src_dir / 'alembic.ini'))
            and confirm('Upgrade database?', default=False)
    ):
        # Note: stopping the app is not strictly necessary, because
        #       the alembic revisions run in separate transactions!
        stop.execute_inner(app, maintenance_hours=app.deploy_duration)
        alembic_upgrade_head(app, ctx)
    else:
        stop.execute_inner(app)  # pragma: no cover

    pip_freeze(app)

    start.execute_inner(app)
    check(app)
    if env.environment == 'production':
        systemd.enable(app, pathlib.Path(os.getcwd()) / 'systemd')


def require_bower(app, d=None):
    d = d or app.static_dir
    if exists(str(d / 'bower.json')):
        require.deb.packages(['npm', 'nodejs'])
        sudo('npm install -g bower@1.8.8')
        with cd(str(d)):
            sudo('bower --allow-root install')


def require_grunt(app, d=None):
    d = d or app.static_dir
    if exists(str(d / 'Gruntfile.js')):
        require.deb.packages(['npm', 'nodejs'])
        sudo('npm install -g grunt-cli@1.3.2')
        with cd(str(d)):
            sudo('npm install')
            sudo('grunt')


def require_postgres(app, drop=False):
    if drop:
        with cd('/var/lib/postgresql'):
            sudo('dropdb %s' % app.name, user='postgres')

    with shell_env(SYSTEMD_PAGER=''):
        require.postgres.server()
        require.postgres.user(app.name, password=app.name,
                encrypted_password=True)
        require.postgres.database(app.name, owner=app.name)

    pg_dir, = run('find /usr/lib/postgresql/ -mindepth 1 -maxdepth 1 -type d').splitlines()
    pg_version = pathlib.PurePosixPath(pg_dir).name

    if app.pg_unaccent:
        sql = 'CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;'
        sudo('psql -c "%s" -d %s' % (sql, app.name), user='postgres')
        # focal already supports combining diacritics
        if system.distrib_codename() in ('xenial', 'bionic'):
            rules_file = '/usr/share/postgresql/%s/tsearch_data/unaccent.rules' % pg_version
            # work around `sudo_upload_template` throwing a 'size mismatch in put'...
            if files.is_file(rules_file):
                files.remove(rules_file, use_sudo=True)
            require.file(
                rules_file,
                source=TEMPLATE_DIR / 'unaccent.rules',
                mode='644',
                use_sudo=True)


def require_config(filepath, app, ctx):
    # We only set add a setting clld.files, if the corresponding directory exists;
    # otherwise the app would throw an error on startup.
    files_dir = app.www_dir / 'files'
    files = files_dir if exists(str(files_dir)) else None
    sudo_upload_template('config.ini', dest=str(filepath), context=ctx, files=files)

    if app.stack == 'django' and confirm('Recreate secret key?', default=True):
        key_chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        secret_key = "".join([random.choice(key_chars) for i in range(50)])
        require.file(
            str(filepath.parent / 'secret_key'), contents=secret_key, use_sudo=True, mode='644')


def require_venv(directory, require_packages=None, assets_name=None, requirements=None):
    require.directory(str(directory), use_sudo=True)

    with settings(sudo_prefix=env.sudo_prefix + ' -H'):  # set HOME for pip log/cache
        require.python.virtualenv(str(directory), venv_python='python3', use_sudo=True)

        with python.virtualenv(str(directory)):
            if require_packages:
                require.python.packages(require_packages, use_sudo=True)
            if requirements:
                require.python.requirements(requirements, use_sudo=True)
            if assets_name:
                sudo('webassets -m %s.assets build' % assets_name)


def require_logging(log_dir, logrotate, access_log, error_log):
    require.directory(str(log_dir), use_sudo=True)

    if env.environment == 'production':
        sudo_upload_template('logrotate.conf', dest=str(logrotate),
                             access_log=access_log, error_log=error_log)


def require_nginx(ctx):
    app = ctx['app']

    with shell_env(SYSTEMD_PAGER=''):
        require.nginx.server()

    auth = http_auth(app)

    # TODO: consider require.nginx.site
    upload_app = functools.partial(
        sudo_upload_template,
        'nginx-app.conf',
        context=ctx,
        clld_dir=get_clld_dir(app.venv_dir) if app.stack == 'clld' else '',
        auth=auth)

    sudo_upload_template('nginx-default.conf', dest=str(app.nginx_default_site), env=env)
    if env.environment != 'test':
        upload_app(dest=str(app.nginx_site))
        nginx.enable(app.nginx_site.name)
    else:  # test environment
        require.directory(str(app.nginx_location.parent), use_sudo=True)
        upload_app(dest=str(app.nginx_location))


def get_clld_dir(venv_dir):  # pragma: no cover
    # /usr/venvs/<app_name>/local/lib/python<version>/site-packages/clld/__init__.pyc
    with python.virtualenv(str(venv_dir)):
        stdout = sudo('python -c "import clld; print(clld.__file__)"')
    clld_path = pathlib.PurePosixPath(stdout.split()[-1])
    return clld_path.parent


def http_auth(app):
    if not (app.public and env.environment == 'production'):
        pwd = helpers.getpwd(app.name, accept_empty=True)
        require.directory(str(app.nginx_htpasswd.parent), use_sudo=True)
        sudo('htpasswd -bc {passwdfile} {username} {password}'
             .format(passwdfile=app.nginx_htpasswd,
                     username=app.name,
                     password=pwd))
        auth = ('proxy_set_header Authorization $http_authorization;\n'
                'proxy_pass_header Authorization;\n'
                'auth_basic "{protected_area_name}";\n'
                'auth_basic_user_file {passwdfile};\n'
                .format(protected_area_name=app.name, passwdfile=app.nginx_htpasswd))
        return auth
    return ''


@task_app_from_environment
def upload_dump(app):
    """Dump local DB and upload it to remote /tmp"""
    upload_sqldump(app, load=False)


def upload_sqldump(app, load=True):
    if app.dbdump:
        if re.match('http(s)?://', app.dbdump):
            fname = 'dump.sql.gz'
            url = app.dbdump
            auth = ''
        else:
            latest = cdstar.get_latest_bitstream(app.dbdump)
            fname, url = latest.name, latest.url
            auth = '-u"{0}:{1}" '.format(os.environ['CDSTAR_USER_BACKUP'],
                                         os.environ['CDSTAR_PWD_BACKUP'])
        target = pathlib.PurePosixPath('/tmp') / fname
        run('curl -s -o {0} {1} {2}'.format(target, auth, url))
    else:
        db_name = prompt('Replace with dump of local database:', default=app.name)
        # TODO: tempfile.mktemp is deprecated.
        # cf. https://docs.python.org/3/library/tempfile.html#tempfile.mktemp
        sqldump = pathlib.Path(tempfile.mktemp(suffix='.sql.gz', prefix='%s-' % db_name))
        target = pathlib.PurePosixPath('/tmp') / sqldump.name
        db_user = '-U postgres ' if PLATFORM == 'windows' else ''
        local('pg_dump %s--no-owner --no-acl -Z 9 -f %s %s' % (db_user, sqldump, db_name))
        print('uploading {0} [{1}]'.format(sqldump, misc.format_size(sqldump.stat().st_size)))
        require.file(str(target), source=str(sqldump))
        sqldump.unlink()

    if load:
        # TODO: assert supervisor.process_status(app.name) != 'RUNNING'
        if postgres.database_exists(app.name):
            require_postgres(app, drop=True)

        sudo('gunzip -c %s | psql -d %s' % (target, app.name), user=app.name)
        sudo('vacuumdb -zf %s' % app.name, user='postgres')
        files.remove(str(target))
    else:
        print(str(target))


@task_app_from_environment
def download_backups(app, d):  # pragma: no cover
    """download db dumps from cdstar."""
    cdstar.download_backups(app.dbdump, pathlib.Path(d))


def alembic_upgrade_head(app, ctx):  # only tested implicitly
    with python.virtualenv(str(app.venv_dir)), cd(str(app.src_dir)):
        sudo('%s -n production upgrade head' % (app.alembic), user=app.name)

    if confirm('Vacuum database?', default=False):
        flag = '-f ' if confirm('VACUUM FULL?', default=False) else ''
        sudo('vacuumdb %s-z -d %s' % (flag, app.name), user='postgres')
