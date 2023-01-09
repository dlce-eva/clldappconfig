# test_deployment.py

import argparse
import pathlib
import pytest
from collections import namedtuple

from clldappconfig import tasks
from clldappconfig.tasks import deployment


pytestmark = pytest.mark.usefixtures("APP")


@pytest.fixture(autouse=True)
def init_cfg(mocker, testdir, config):
    mocker.patch.multiple(
        "clldappconfig.tasks.deployment.appconfig", APPS=config, APPS_DIR=testdir
    )


@pytest.fixture()
def mocked_deployment(mocker):
    def run(cmd, *args, **kwargs):
        if cmd.startswith("curl"):
            return '{"status": "ok"}'
        elif cmd.startswith("pip freeze"):
            return (
                "You should test all your code\n"
                "test==1.0.0\n"
                "clld==8.0.1\n"
                "clld-glottologfamily-plugin==4.0.0\n"
                "clldmpg==4.2.0\n"
                "clldutils==3.10.1\n"
            )
        elif cmd.startswith("find"):
            return "./somfile"
        else:
            return ""

    getpwd = mocker.Mock(return_value="password")
    mocker.patch("clldappconfig.tasks.helpers.getpwd", getpwd)
    get_latest_bitstream = mocker.Mock(
        return_value=namedtuple("NamedBitstream", "name, url")(
            "bs_dump.sql.gz", "https://example.com"
        )
    )
    mocked = mocker.patch.multiple(
        "clldappconfig.tasks.deployment",
        cd=mocker.DEFAULT,
        cdstar=mocker.Mock(get_latest_bitstream=get_latest_bitstream),
        confirm=mocker.Mock(return_value=True),
        exists=mocker.Mock(return_value=True),
        files=mocker.DEFAULT,
        letsencrypt=mocker.Mock(),
        local=mocker.Mock(),
        nginx=mocker.Mock(),
        pathlib=mocker.DEFAULT,
        postgres=mocker.Mock(),
        prompt=mocker.Mock(return_value="app"),
        python=mocker.DEFAULT,
        require=mocker.Mock(),
        run=mocker.Mock(side_effect=run),
        service=mocker.Mock(),
        sudo=mocker.Mock(return_value="/usr/venvs/__init__.py"),
        supervisor=mocker.Mock(),
        system=mocker.Mock(
            **{
                "distrib_id.return_value": "Ubuntu",
                "distrib_codename.return_value": "focal",
            }
        ),
        time=mocker.Mock(),
    )
    return argparse.Namespace(getpwd=getpwd, **mocked)


@pytest.fixture
def mocked_ctx(mocker, config):
    mocker.patch.multiple(
        "clldappconfig.tasks.deployment", prompt=mocker.Mock(return_value="test")
    )
    env = mocker.patch("clldappconfig.tasks.deployment.env")
    env.configure_mock(host="vbox", environment="production")

    return deployment.template_context(tasks.APP)


def test_template_context(mocked_ctx):
    assert mocked_ctx["PRODUCTION_HOST"] is True
    assert mocked_ctx["app"].name == "testapp"


def test_sudo_upload_template(mocked_ctx, mocker, config):
    files = mocker.patch("clldappconfig.tasks.deployment.files")

    deployment.sudo_upload_template(
        "template", "/dst", mocked_ctx, app=config["testapppublic"]
    )

    _, call_args, call_kwargs = files.mock_calls[0]
    assert call_args[0] == "template"
    assert call_args[1] == "/dst"
    assert call_kwargs["template_dir"].endswith("clldappconfig/templates")


@pytest.fixture
def mocked_appsdir(mocker, tmp_path):
    # create a temporary APPS_DIR
    mocker.patch("clldappconfig.tasks.deployment.appconfig.APPS_DIR", tmp_path)
    appsdir = tmp_path / tasks.APP.name
    appsdir.mkdir(exist_ok=True)
    return appsdir


def test_pip_freeze(mocked_deployment, mocked_appsdir, capsys):
    deployment.pip_freeze(tasks.APP, packages="test")

    out, _ = capsys.readouterr()
    assert out == "test==1.0.0\n"
    with open(mocked_appsdir / "requirements.txt", "r") as reqtxt:
        lines = reqtxt.read().splitlines()
        assert len(lines) == 5
        assert all([line.startswith("clld") for line in lines[1:]])


def test_check(mocked_deployment, mocker, config):
    mocker.patch("clldappconfig.tasks.APP", config["testapppublic"])
    env = mocker.patch("clldappconfig.tasks.deployment.env")
    env.configure_mock(host="vbox", environment="production")
    deployment.check(tasks.APP)


def test_upgrade(mocked_appsdir, mocked_deployment, capsys):
    tasks.upgrade("production", test="1.0.0")
    out, _ = capsys.readouterr()
    assert "test==1.0.0" in out


@pytest.mark.parametrize("continue_anyways", [True, False])
def test_deploy_outdated(mocked_deployment, mocker, capsys, continue_anyways):
    """Test behavior if local git master is behind upstream"""
    mocker.patch.multiple(
        "clldappconfig.tasks.deployment",
        misc=mocker.Mock(),
        local=mocker.Mock(side_effect=["asdf1234", "qwer5678"]),
        confirm=mocker.Mock(return_value=continue_anyways),
    )

    if continue_anyways:
        with pytest.raises(FileNotFoundError):
            tasks.deploy("production")
        out, _ = capsys.readouterr()
        assert "Continuing deployment." in out
    else:
        tasks.deploy("production")
        out, _ = capsys.readouterr()
        assert out.splitlines()[-1] == "Deployment aborted."


# ---------------- old tests ----------------


def test_deploy_distrib(mocker):
    di = mocker.patch("clldappconfig.tasks.deployment.system.distrib_id")
    di.return_value = "nondistribution"
    with pytest.raises(AssertionError):
        tasks.deploy("production")

    di.return_value = "Ubuntu"
    mocker.patch(
        "clldappconfig.tasks.deployment.system.distrib_codename",
        return_value="noncodename",
    )
    with pytest.raises(ValueError, match="unsupported platform"):
        tasks.deploy("production")


def test_deploy_public(mocker, config, mocked_deployment):
    mocker.patch("clldappconfig.tasks.APP", config["testapppublic"])
    mocker.patch("clldappconfig.tasks.deployment.misc", mocker.Mock())

    with pytest.raises(FileNotFoundError):
        tasks.deploy("production")

    assert not mocked_deployment.getpwd.called


@pytest.mark.parametrize(
    "environment, with_alembic",
    [("production", True), ("production", False), ("test", True), ("test", False)],
)
def test_deploy(
    mocker, config, mocked_deployment, mocked_appsdir, environment, with_alembic
):
    mocker.patch("clldappconfig.tasks.deployment.misc", mocker.Mock())

    tasks.deploy(environment, with_alembic=with_alembic)

    assert mocked_deployment.getpwd.call_count == 1


def test_require_misc(mocked_deployment, mocker):
    # These functions all just run a bunch of fabric commands to install
    # dependencies.  Since we mock all fabric functions there really isn't
    # anything meaningfull to test.  We can still call these functions as some
    # kind of syntax check and to get 100% coverage.
    #
    # Maybe consider using '# pragma: no cover' instead.
    mocker.patch("clldappconfig.tasks.APP.stack", "django")
    env = mocker.patch("clldappconfig.tasks.deployment.env")
    env.configure_mock(environment="production")
    deployment.require_bower(tasks.APP)
    deployment.require_grunt(tasks.APP)
    deployment.require_postgres(tasks.APP, drop=True)
    deployment.require_config(
        tasks.APP.config, tasks.APP, deployment.template_context(tasks.APP)
    )
    deployment.require_venv(
        "dir/", require_packages="test1", assets_name="test2", requirements="test3"
    )
    deployment.require_logging("logdir/", "logrotate/dir/", None, None)
    deployment.require_nginx(deployment.template_context(tasks.APP))
    assert True


def test_http_auth(mocked_deployment, mocker):
    sudo = mocker.patch("clldappconfig.tasks.deployment.sudo")
    auth = deployment.http_auth(tasks.APP)
    assert 'auth_basic "testapp";\n' in auth
    sudo.assert_has_calls(
        [
            mocker.call(
                "htpasswd -bc /etc/nginx/htpasswd/testapp.htpasswd testapp password"
            )
        ],
        any_order=False,
    )


def test_upload_dump(mocked_deployment, mocker, capsys):
    # override the mock from mocked_deployment.
    # TODO: check if we really need the pathlib mock in mocked_deployment or
    # alter the mock there
    mocker.patch(
        "clldappconfig.tasks.deployment.pathlib.PurePosixPath",
        mocker.Mock(side_effect=lambda x: pathlib.PurePosixPath(x)),
    )
    tasks.upload_dump("production")
    out, _ = capsys.readouterr()
    assert out.splitlines()[-1] == "/tmp/dump.sql.gz"


@pytest.fixture
def mocked_pathlib(mocker):
    class MockedFile:
        name = "no_dump.sql.gz"

        def stat(self):
            stats = mocker.Mock()
            stats.configure_mock(st_size=1024)
            return stats

        def unlink(self):
            pass

        def __str__(self):
            return "/tmp/{}".format(self.name)

    def ppp(x):
        if x == "/tmp":
            return pathlib.PurePosixPath("/tmp")
        else:
            return mocker.Mock()

    mocker.patch.multiple(
        "clldappconfig.tasks.deployment.pathlib",
        Path=mocker.Mock(return_value=MockedFile()),
        PurePosixPath=ppp,
    )


def test_upload_sqldump_load(mocked_deployment, mocked_pathlib):
    deployment.upload_sqldump(tasks.APP, load=True)
    mocked_deployment.files.remove.assert_called_with("/tmp/dump.sql.gz")


def test_upload_sqldump_url(mocked_deployment, mocked_pathlib, capsys):
    deployment.upload_sqldump(tasks.APP, load=False)
    out, _ = capsys.readouterr()
    assert out.splitlines()[-1] == "/tmp/dump.sql.gz"


def test_upload_sqldump_bs(
    mocked_deployment, mocked_pathlib, mocker, capsys, monkeypatch
):
    monkeypatch.setattr(tasks.APP, "dbdump", "ASDF1234")
    mocker.patch.dict(
        "clldappconfig.tasks.deployment.os.environ",
        {"CDSTAR_USER_BACKUP": "u", "CDSTAR_PWD_BACKUP": "p"},
    )

    deployment.upload_sqldump(tasks.APP, load=False)
    out, _ = capsys.readouterr()
    assert out.splitlines()[-1] == "/tmp/bs_dump.sql.gz"


def test_upload_sqldumo_nodump(mocked_deployment, mocked_pathlib, capsys, monkeypatch):
    monkeypatch.setattr(tasks.APP, "dbdump", "")
    deployment.upload_sqldump(tasks.APP, load=False)
    out, _ = capsys.readouterr()
    assert out.splitlines()[-1] == "/tmp/no_dump.sql.gz"
