# conftest.py - pytest fixtures
import pathlib
import pytest

import clldappconfig as appconfig
from clldappconfig.config import Config


@pytest.fixture(scope="session")
def testdir():
    return pathlib.Path(__file__).parent


@pytest.fixture(scope="session")
def config(testdir):
    appconfig.init(testdir / "apps")
    result = Config.from_file(str(testdir / "apps/apps.ini"))
    return result


@pytest.fixture(scope="session")
def app(config, name="testapp"):
    return config[name]


@pytest.fixture
def APP(mocker, app):
    yield mocker.patch("clldappconfig.tasks.APP", app)
