import os

from pycdstar.api import Cdstar
from cdstarcat.resources import RollingBlob
from clldutils.misc import format_size

SERVICE_URL = os.environ.get("CDSTAR_URL")
USER = os.environ.get("CDSTAR_USER")
PWD = os.environ.get("CDSTAR_PWD")


class NamedBitstream(object):
    def __init__(self, oid, bs):
        self.oid = oid
        self.bitstream = bs

    @property
    def datetime(self):
        return RollingBlob.parse_timestamp(self.name)

    @property
    def size(self):
        return self.bitstream._properties["filesize"]

    @property
    def size_h(self):
        return format_size(self.size)

    @property
    def url(self):
        return "{0}/bitstreams/{1}/{2}".format(SERVICE_URL, self.oid, self.name)

    @property
    def name(self):
        return self.bitstream.id


def get_api():
    return Cdstar(service_url=SERVICE_URL, user=USER, password=PWD)


def add_backup_user(oid):
    obj = get_api().get_object(oid)
    obj.acl.update(read=["backup", "clld"], write=["backup", "clld"])


def get_bitstreams(oid):
    rb = RollingBlob(oid=oid)
    return [NamedBitstream(oid, bs) for bs in rb.sorted_bitstreams(get_api())]


def get_latest_bitstream(oid):
    bs = RollingBlob(oid=oid).latest(get_api())
    if bs:
        return NamedBitstream(oid, bs)


def add_bitstream(oid, fname):
    rb = RollingBlob(oid=oid)
    api = get_api()
    # Add the sql dump as latest bitstream ...
    rb.add(api, str(fname))


def download_backups(oid, d):
    api = get_api()
    obj = api.get_object(oid)
    for i, bs in enumerate(reversed(obj.bitstreams)):
        if i % 5 == 0:
            if not d.joinpath(bs.id).exists():
                with d.joinpath(bs.id).open("wb") as fp:
                    fp.write(bs.read().read())
