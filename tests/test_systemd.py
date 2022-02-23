from appconfig import systemd


def test_enable(app, testdir, mocker):
    files = mocker.Mock(upload_template=mocker.Mock())
    mocker.patch('appconfig.systemd.files', files)
    mocker.patch('appconfig.systemd.sudo')
    systemd.enable(app, testdir / 'systemd')
    assert files.upload_template.call_count == 3


def test_uninstall(app, testdir, mocker):
    mocker.patch('appconfig.systemd.files.exists', mocker.Mock(return_value=True))
    mock = mocker.patch('appconfig.systemd.sudo')
    systemd.uninstall(app, testdir / 'systemd')
    deletetions = ['rm /etc/systemd/system/testapp-unit.service',
                   'rm /etc/systemd/system/testapp-unit.timer',
                   'rm /usr/bin/testapp-unit']
    for c in deletetions:
        assert mocker.call(c) in mock.mock_calls
