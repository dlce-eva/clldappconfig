# conftest.py - pytest fixtures
import pathlib
import pytest

import appconfig
from appconfig.config import Config


@pytest.fixture(scope='session')
def testdir():
    return pathlib.Path(__file__).parent


@pytest.fixture(scope='session')
def config(testdir):
    with pytest.warns(UserWarning, match='missing fabfile dir: testapp'):
        appconfig.init(testdir)
        result = Config.from_file(str(testdir / 'apps.ini'))
    return result


@pytest.fixture(scope='session')
def app(config, name='testapp'):
    return config[name]


@pytest.fixture
def APP(mocker, app):
    yield mocker.patch('appconfig.tasks.APP', app)
