import clldappconfig as appconfig
import pathlib
import pytest


def test_init(testdir):
    cfg_dir = pathlib.Path(testdir) / "apps/"
    with pytest.raises(FileNotFoundError, match=".* is not a directory"):
        appconfig.init("does/not/exist")
    with pytest.raises(FileNotFoundError, match=".* does not exist"):
        appconfig.init(testdir)

    appconfig.init(cfg_dir)
    assert appconfig.APPS_DIR == cfg_dir
    assert appconfig.CONFIG_FILE == cfg_dir / "apps.ini"
    assert "testapp" in appconfig.APPS
