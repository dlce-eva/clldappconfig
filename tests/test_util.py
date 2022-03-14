import pytest

from clldappconfig import util


@pytest.mark.parametrize('keyserver', ['example.com', ['--keyserver example.com'], None])
def test_ppa(mocker, keyserver):
    mocker.patch.multiple('clldappconfig.util',
                          distrib_release=mocker.Mock(return_value=20.04),
                          distrib_codename=mocker.Mock(return_value='focal'),
                          is_file=mocker.Mock(return_value=False),
                          package=mocker.DEFAULT,
                          run_as_root=mocker.DEFAULT)
    update_index = mocker.patch('clldappconfig.util.update_index')

    util.ppa('ppa:chris-lea/node.js', keyserver=keyserver)
    update_index.assert_called()
