from clldappconfig import cdstar
import datetime
import pathlib
import pytest


@pytest.fixture(autouse=True)
def mock_cdstar_config(mocker):
    mocker.patch.multiple(
        "clldappconfig.cdstar", SERVICE_URL="http://example.org/", USER="u", PWD="pwd"
    )


@pytest.fixture
def mock_rb(mocker):
    class RB(mocker.Mock):
        add = mocker.Mock()
        _sorted_bitstreams = [mocker.Mock(), mocker.Mock()]

        def sorted_bitstreams(self, _):
            return self._sorted_bitstreams

        def latest(self, _):
            return self._sorted_bitstreams[0]

    return mocker.patch("clldappconfig.cdstar.RollingBlob", RB)


def test_get_api():
    api = cdstar.get_api()
    assert api.service_url == "http://example.org/"
    assert api.session.auth == ("u", "pwd")


def test_NamedBitstream(mocker):
    class Bitstream:
        id = "y"
        _properties = {"filesize": 1024}

    nbs = cdstar.NamedBitstream("x", Bitstream())
    assert "example.org" in nbs.url
    assert nbs.name == "y"
    assert nbs.size_h == "1.0KB"
    #  if the name of NamedBitstream is not a valid date, we get the 1900-01-01
    assert nbs.datetime == datetime.datetime(1900, 1, 1, 0, 0)


def test_add_bitstream(mocker, testdir, mock_rb):
    cdstar.add_bitstream("oid", testdir / "apps.ini")
    assert mock_rb.add.called


def test_add_backup_user(mocker):
    obj = mocker.Mock()
    mocker.patch(
        "clldappconfig.cdstar.Cdstar.get_object", mocker.Mock(return_value=obj)
    )
    cdstar.add_backup_user("oid")
    obj.acl.update.assert_called()


def test_get_bitstream(mock_rb):
    streams = cdstar.get_bitstreams("oid")
    assert len(streams) == 2


def test_get_latest_bitstream(mock_rb):
    stream = cdstar.get_latest_bitstream("oid")
    assert stream


def test_download_backups(mocker, tmpdir):
    class Bitstream:
        id = "y"

        def read(self):
            f = mocker.Mock()
            f.configure_mock(read=mocker.Mock(return_value=b"loremipsum\n"))
            return f

    obj = mocker.Mock()
    obj.configure_mock(bitstreams=[Bitstream()])
    mocker.patch(
        "clldappconfig.cdstar.Cdstar.get_object", mocker.Mock(return_value=obj)
    )

    p = pathlib.Path(tmpdir)
    cdstar.download_backups("oid", p)
    assert p.joinpath("y").exists()
