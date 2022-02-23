# test_tasks.py
import pytest
from appconfig import tasks


def test_init(mocker, app_name='nonname'):
    mocker.patch('appconfig.APPS', {app_name: mocker.sentinel.app})

    try:
        tasks.init(app_name)
        assert tasks.APP is mocker.sentinel.app
    finally:
        tasks.APP = None


@pytest.fixture
def testtasks(APP, monkeypatch):
    monkeypatch.setattr(tasks.fabric.api.env, 'hosts', [])

    def test_func(app):
        return app.name

    task1 = tasks.task_app_from_environment(test_func)
    task2 = tasks.task_app_from_environment('production')(test_func)
    return task1, task2


def test_task_app_from_environment(testtasks):
    task1, task2 = testtasks
    assert task1('production')['vbox'] == 'testapp'
    assert task2()['vbox'] == 'testapp'


def test_task_app_from_environment_no_host(testtasks):
    task, _ = testtasks
    with pytest.raises(ValueError):
        task('staging')


def test_tasks(mocker, APP):
    mocker.patch('appconfig.tasks.fabric.api.execute', autospec=True)

    tasks.deploy('test')
    tasks.start('test')
    tasks.stop('test')
    tasks.uninstall('test')
    tasks.run_script('test', 'script')
    tasks.create_downloads('test')
    tasks.copy_rdfdump('test')
