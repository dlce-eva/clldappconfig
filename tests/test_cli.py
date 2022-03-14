import logging
from urllib.error import HTTPError

import pytest
import pathlib

from clldappconfig.__main__ import main


def test_with_parsed_args():
    assert main(parsed_args='something invalid') == 1


@pytest.mark.parametrize('log', [None, logging.getLogger(None)])
def test_ls(capsys, log):
    cfg_dir = pathlib.Path(__file__).parent / 'apps'

    main(['-c', 'does/not/exist', 'ls'])

    out, err = capsys.readouterr()
    assert out == 'does/not/exist is not a directory\n'

    main(['-c', str(cfg_dir), 'ls'], log=log)

    out, err = capsys.readouterr()
    assert 'testapp' in out

    main(['-c', str(cfg_dir), 'ls', '-p'], log=log)

    out, err = capsys.readouterr()
    assert 'testapp' in out


def test_error(mocker):
    cfg_file = pathlib.Path(__file__).parent / 'apps'
    mocker.patch('clldappconfig.commands.test_error.urlopen')

    with pytest.raises(RuntimeError):
        main(['-c', str(cfg_file), 'test_error', 'testapp'])

    mocker.patch(
        'clldappconfig.commands.test_error.urlopen',
        mocker.Mock(side_effect=HTTPError('', 500, '', {}, None)))
    main(['-c', str(cfg_file), 'test_error', 'testapp'])
