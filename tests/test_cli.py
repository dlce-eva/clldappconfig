import logging
from urllib.error import HTTPError

import pytest

from appconfig.__main__ import main


@pytest.mark.xfail
def test_with_parsed_args():
    assert main(parsed_args='something invalid') == 1


@pytest.mark.xfail
@pytest.mark.parametrize('log', [None, logging.getLogger(None)])
def test_ls(capsys, log):
    main(['ls'], log=log)
    out, err = capsys.readouterr()
    assert 'wals3' in out

    main(['ls', '-p'], log=log)
    out, err = capsys.readouterr()
    assert 'wals3' in out


@pytest.mark.xfail
def test_error(mocker):
    mocker.patch('appconfig.commands.test_error.urlopen')

    with pytest.raises(RuntimeError):
        main(['test_error', 'wals3'])

    mocker.patch(
        'appconfig.commands.test_error.urlopen',
        mocker.Mock(side_effect=HTTPError('', 500, '', {}, None)))
    main(['test_error', 'wals3'])
