from clldappconfig.tasks import letsencrypt
from clldappconfig import tasks


def test_require_cert(APP, config, mocker):
    sudo = mocker.patch('clldappconfig.tasks.letsencrypt.sudo')
    mocker.patch('clldappconfig.tasks.letsencrypt.clldappconfig.APPS', config)

    letsencrypt.require_cert(tasks.APP)
    letsencrypt.require_cert('example.com')

    for call in sudo.call_args_list:
        print(call)
        cmd, = call[0]
        assert 'www.testapp.test.clld.org' in cmd or 'example.com' in cmd
