# test_tasks.py
import pytest
from clldappconfig import tasks


def test_init(mocker, testdir):
    mocker.patch(
        "clldappconfig.tasks.helpers.caller_dir", return_value=testdir / "apps/testapp/"
    )

    try:
        tasks.init("testapp")
        assert tasks.APP.name == "testapp"
    finally:
        tasks.APP = None


def test_init_environ(mocker, testdir):
    mocker.patch("clldappconfig.tasks.os.environ", {"APPCONFIG_DIR": testdir / "apps/"})

    try:
        tasks.init("testapp")
        assert tasks.APP.name == "testapp"
    finally:
        tasks.APP = None


@pytest.fixture
def testtasks(APP, monkeypatch):
    monkeypatch.setattr(tasks.fabric.api.env, "hosts", [])

    def test_func(app):
        return app.name

    task1 = tasks.task_app_from_environment(test_func)
    task2 = tasks.task_app_from_environment("production")(test_func)
    return task1, task2


def test_task_app_from_environment(testtasks):
    task1, task2 = testtasks
    assert task1("production")["vbox"] == "testapp"
    assert task2()["vbox"] == "testapp"


def test_task_app_from_environment_no_host(testtasks):
    task, _ = testtasks
    with pytest.raises(ValueError):
        task("staging")


def test_tasks(mocker, APP):
    mocker.patch("clldappconfig.tasks.fabric.api.execute", autospec=True)

    tasks.deploy("test")
    tasks.start("test")
    tasks.stop("test")
    tasks.uninstall("test")
    tasks.run_script("test", "script")
    tasks.create_downloads("test")
    tasks.copy_rdfdump("test")
