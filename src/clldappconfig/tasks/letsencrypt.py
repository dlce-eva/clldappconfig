from fabric.api import sudo
from fabtools import require

from clldappconfig import APPS
from clldappconfig.config import App

from clldappconfig import util
from fabtools.system import distrib_codename


def require_certbot():  # pragma: nocover
    if distrib_codename() == 'focal':
        require.deb.package('certbot python3-certbot-nginx')
    else:
        require.deb.package('software-properties-common')
        util.ppa('ppa:certbot/certbot', lsb_codename=distrib_codename())
        require.deb.package('python-certbot-nginx')


def require_cert(domain):
    if isinstance(domain, App):
        domains = domain.domain
        if domain.with_www_subdomain:
            domains += ',www.{0}'.format(domain.domain)
    else:
        domains = domain
    # If an App instance is passed, we lookup its domain attribute:
    sudo('certbot --nginx -n -d {0} certonly --agree-tos --expand --email {1}'.format(
        domains, APPS.defaults['error_email']))


def delete(cert):  # pragma: nocover
    sudo('certbot delete --cert-name {0}'.format(cert))


def renew():  # pragma: nocover
    sudo('certbot --nginx -n renew')
