# appconfig - remote control for DLCE apps

import pathlib

from . import config

__all__ = ['APPS_DIR', 'CONFIG_FILE', 'APPS', 'init']

APPS_DIR = None

CONFIG_FILE = None

APPS = None


def init(config_dir):
    """Initialize global variables and configuration.
    """
    global APPS_DIR, CONFIG_FILE, APPS

    APPS_DIR = pathlib.Path(config_dir)
    if not APPS_DIR.is_dir():
        raise FileNotFoundError('{} is not a directory'.format(APPS_DIR))

    CONFIG_FILE = APPS_DIR / 'apps.ini'
    if not CONFIG_FILE.exists():
        raise FileNotFoundError('{} does not exist'.format(CONFIG_FILE))

    APPS = config.Config.from_file(CONFIG_FILE)


# TODO: consider https://pypi.python.org/pypi/pyvbox
#       for scripting tests with virtualbox
