from fabtools.deb import (
    update_index,
)
from fabtools.files import is_file
from fabtools.require.deb import package
from fabtools.system import distrib_codename, distrib_release
from fabtools.utils import run_as_root


def ppa(name, auto_accept=True, keyserver=None, lsb_codename=None):
    """
    Require a `PPA`_ package source.

    Example::

        from fabtools import require

        # Node.js packages by Chris Lea
        require.deb.ppa('ppa:chris-lea/node.js', keyserver='my.keyserver.com')

    .. _PPA: https://help.launchpad.net/Packaging/PPA
    """
    assert name.startswith("ppa:")

    user, repo = name[4:].split("/", 2)

    release = float(distrib_release())

    repo = repo.replace(".", "_")
    auto_accept = "--yes" if auto_accept else ""

    if not isinstance(keyserver, str) and keyserver:
        keyserver = keyserver[0]
    if keyserver:
        keyserver = "--keyserver " + keyserver
    else:
        keyserver = ""

    distrib = distrib_codename()
    source = "/etc/apt/sources.list.d/%(user)s-%(repo)s-%(distrib)s.list" % locals()

    if not is_file(source):
        package("software-properties-common")
        run_as_root(
            "add-apt-repository %(auto_accept)s %(keyserver)s %(name)s" % locals(),
            pty=False,
        )
        update_index()
