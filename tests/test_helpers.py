from clldappconfig import helpers


def test_getpwd(mocker):
    mocker.patch('clldappconfig.helpers.getpass',
                 mocker.Mock(getpass=mocker.Mock(return_value='abc')))
    assert helpers.getpwd('x') == 'abc'
    assert helpers.getpwd('x', accept_empty=True) == 'abc'


def test_caller_dirname():
    path = helpers.caller_dirname(0)
    assert path == 'tests'


def test_duplicates():
    assert helpers.duplicates([1, 2, 2, 3, 1]) == [2, 1]


def test_strfnow():
    assert helpers.strfnow() < helpers.strfnow(add_hours=1)
