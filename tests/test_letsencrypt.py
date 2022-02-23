from appconfig.tasks import letsencrypt
from appconfig import tasks


def test_require_cert(APP, config, mocker):
    sudo = mocker.patch('appconfig.tasks.letsencrypt.sudo')
    mocker.patch('appconfig.tasks.letsencrypt.APPS', config)

    letsencrypt.require_cert(tasks.APP)
    letsencrypt.require_cert('example.com')

    for call in sudo.call_args_list:
        print(call)
        cmd, = call[0]
        assert 'www.testapp.test.clld.org' in cmd or 'example.com' in cmd
