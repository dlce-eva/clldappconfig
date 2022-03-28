import pytest
from clldappconfig import tasks


@pytest.fixture
def mocked_bitstream(mocker):
    m = mocker.Mock()
    m.configure_mock(id="db_dump_TEST", _properties={"filesize": 42})
    mocker.patch(
        "clldappconfig.tasks.other.cdstar.RollingBlob.sorted_bitstreams",
        return_value=[m],
    )
    return m


def test_list_dumps(APP, mocked_bitstream, capsys):
    tasks.list_dumps("production")
    out, _ = capsys.readouterr()
    assert out.splitlines()[1].startswith("1\t1900-01-01T00:00:00")


def test_remove_dumps(APP, mocked_bitstream):
    tasks.remove_dumps("production", keep=0)
    mocked_bitstream.delete.assert_called_once()


def test_remove_single_dump(APP, mocked_bitstream):
    tasks.remove_single_dump("production", "db_dump_TEST")
    tasks.remove_single_dump("production", "db_dump_TEST2")
    # as db_dump_TEST2 doesn't exist, delete was only called once
    mocked_bitstream.delete.assert_called_once()


@pytest.mark.parametrize(
    "psql_exception, confirm_ret_val, local_ret_val",
    [
        (None, True, 1),
        (FileNotFoundError(), True, 1),
        (None, False, 1),
        (None, True, 0),
    ],
)
def test_load_db(
    APP, mocker, tmp_path, capsys, psql_exception, confirm_ret_val, local_ret_val
):
    mocker.patch(
        "clldappconfig.tasks.other.subprocess.check_output",
        return_value=b"testapp|user|UTF8|en_US.UTF-8|en_US.UTF-8|\n",
        side_effect=psql_exception,
    )

    db_dump = "testapp-tmp.sql.gz"
    open(tmp_path / db_dump, "a").close()  # create empty file

    confirm = mocker.Mock(return_value=confirm_ret_val)

    local_ret = mocker.Mock()
    local_ret.configure_mock(return_code=local_ret_val)

    mocker.patch.multiple(
        "clldappconfig.tasks.other",
        dump_db=mocker.Mock(return_value=tmp_path / db_dump),
        confirm=confirm,
        local=mocker.Mock(return_value=local_ret),
    )

    tasks.load_db("production")

    out, _ = capsys.readouterr()
    lastline = out.splitlines()[-1]

    if not psql_exception:
        confirm.assert_called_once()

    if local_ret_val == 1:  # all local commands succeed
        assert lastline == "SQL dump downloaded to {}".format(tmp_path / db_dump)
    else:  # local commands fail -> the local db dump should be deleted
        assert lastline.startswith("[vbox]")
        assert not (tmp_path / db_dump).exists()


def test_create_downloads(APP, mocker):
    sudo = mocker.Mock()
    mocker.patch.multiple(
        "clldappconfig.tasks.other",
        sudo=sudo,
        require=mocker.DEFAULT,
        cd=mocker.DEFAULT,
    )

    tasks.create_downloads("production")

    # create a command as in tasks/other/run_script, wich is called by
    # crate_downloads
    pycmd = f"{tasks.APP.venv_bin}/python"
    script = f"{tasks.APP.src_dir / tasks.APP.name}/scripts/create_downloads.py"
    params = f"{tasks.APP.config.name}#{tasks.APP.name}"
    cmd = f"{pycmd} {script} {params} "

    print(cmd)
    print(sudo.call_args_list)
    sudo.assert_called_with(cmd, user=tasks.APP.name)


@pytest.fixture
def mocked_download_dir(tmp_path):
    test_files = ["test1.test", "test2.test", "test3.n3.gz"]
    for f in test_files:
        open(tmp_path / f, "a").close()
    return tmp_path


def test_copy_downloads(APP, mocker, mocked_download_dir):
    require = mocker.patch("clldappconfig.tasks.other.require")
    tasks.copy_downloads("production", mocked_download_dir, "*.test")
    # two *.test files in mocked download dir should result in thow calls to
    # require.file
    assert require.file.call_count == 2


def test_copy_rdfdump(APP, mocker, mocked_download_dir):
    require = mocker.patch("clldappconfig.tasks.other.require")
    tasks.copy_rdfdump("production", mocked_download_dir)
    assert require.file.call_count == 1
