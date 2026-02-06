import hashlib
import io
import os
import tempfile

import pytest

from prepdocslib.listfilestrategy import (
    File,
    LocalListFileStrategy,
)


def test_file_filename():
    empty = io.BytesIO()
    empty.name = "test/foo.pdf"
    assert File(empty).filename() == "foo.pdf"


def test_file_file_extension():
    empty = io.BytesIO()
    empty.name = "test/foo.pdf"
    assert File(empty).file_extension() == ".pdf"


def test_file_contextmanager():
    empty = io.BytesIO()
    empty.name = "test/foo.pdf"
    f = File(empty)
    assert f.content.read() == b""
    f.close()
    assert empty.closed


def test_file_filename_to_id():
    empty = io.BytesIO()
    empty.name = "foo.pdf"
    # test ascii filename
    assert File(empty).filename_to_id() == "file-foo_pdf-666F6F2E706466"
    # test filename containing unicode
    empty.name = "foo\u00a9.txt"
    assert File(empty).filename_to_id() == "file-foo__txt-666F6FC2A92E747874"
    # test filenaming starting with unicode
    empty.name = "ファイル名.pdf"
    assert File(empty).filename_to_id() == "file-______pdf-E38395E382A1E382A4E383ABE5908D2E706466"


def test_file_filename_to_id_acls():
    empty = io.BytesIO()
    empty.name = "foo.pdf"
    filename_id = File(empty).filename_to_id()
    filename_id2 = File(empty, acls={"oids": ["A-USER-ID"]}).filename_to_id()
    filename_id3 = File(empty, acls={"groups": ["A-GROUP-ID"]}).filename_to_id()
    filename_id4 = File(empty, acls={"oids": ["A-USER-ID"], "groups": ["A-GROUP-ID"]}).filename_to_id()
    # Assert that all filenames are unique
    assert len(set([filename_id, filename_id2, filename_id3, filename_id4])) == 4


@pytest.mark.asyncio
async def test_locallistfilestrategy():
    with tempfile.TemporaryDirectory() as tmpdirname:
        for filename in ["a.pdf", "b.pdf", "c.pdf"]:
            with open(os.path.join(tmpdirname, filename), "w") as f:
                f.write("test")
        local_list_strategy = LocalListFileStrategy(path_pattern=f"{tmpdirname}/*")

        # First test that we can get the filepaths
        filepaths = [path async for path in local_list_strategy.list_paths()]
        assert len(filepaths) == 3
        # filepaths come back in non-deterministic order, so sort them
        filepaths = sorted(filepaths)
        assert filepaths[0] == os.path.join(tmpdirname, "a.pdf")
        assert filepaths[1] == os.path.join(tmpdirname, "b.pdf")
        assert filepaths[2] == os.path.join(tmpdirname, "c.pdf")

        # Now test that we can get the files
        files = [file async for file in local_list_strategy.list()]
        assert len(files) == 3
        # files come back in non-deterministic order, so sort them
        files = sorted(files, key=lambda f: f.filename())
        assert files[0].filename() == "a.pdf"
        assert files[1].filename() == "b.pdf"
        assert files[2].filename() == "c.pdf"
        for file in files:
            file.close()


@pytest.mark.asyncio
async def test_locallistfilestrategy_nesteddir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.mkdir(os.path.join(tmpdirname, "test"))
        for filename in ["a.pdf", "b.pdf", "c.pdf"]:
            with open(os.path.join(tmpdirname, "test", filename), "w") as f:
                f.write("test")
        local_list_strategy = LocalListFileStrategy(path_pattern=f"{tmpdirname}/*")

        # First test that we can get the filepaths
        filepaths = [path async for path in local_list_strategy.list_paths()]
        assert len(filepaths) == 3
        # filepaths come back in non-deterministic order, so sort them
        filepaths = sorted(filepaths)
        assert filepaths[0] == os.path.join(tmpdirname, "test", "a.pdf")
        assert filepaths[1] == os.path.join(tmpdirname, "test", "b.pdf")
        assert filepaths[2] == os.path.join(tmpdirname, "test", "c.pdf")

        # Now test that we can get the files
        files = [file async for file in local_list_strategy.list()]
        assert len(files) == 3
        # files come back in non-deterministic order, so sort them
        files = sorted(files, key=lambda f: f.filename())
        assert files[0].filename() == "a.pdf"
        assert files[1].filename() == "b.pdf"
        assert files[2].filename() == "c.pdf"
        for file in files:
            file.close()


def test_locallistfilestrategy_checkmd5():
    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(os.path.join(tmpdirname, "test.pdf"), "w") as pdf_file:
            pdf_file.write("test")
            f1_hash = hashlib.md5(b"test").hexdigest()
        with open(os.path.join(tmpdirname, "test.pdf.md5"), "w", encoding="utf-8") as md5_file:
            md5_file.write(f1_hash)

        local_list_strategy = LocalListFileStrategy(path_pattern=f"{tmpdirname}/*")
        assert local_list_strategy.check_md5(md5_file.name) is True
        assert local_list_strategy.check_md5(pdf_file.name) is True
        # now change the file, hash should no longer match
        with open(os.path.join(tmpdirname, "test.pdf"), "w") as pdf_file:
            pdf_file.write("test2")
        assert local_list_strategy.check_md5(pdf_file.name) is False


@pytest.mark.asyncio
async def test_locallistfilestrategy_global():
    with tempfile.TemporaryDirectory() as tmpdirname:
        for filename in ["a.pdf", "b.pdf", "c.pdf"]:
            with open(os.path.join(tmpdirname, filename), "w") as f:
                f.write("test")
        local_list_strategy = LocalListFileStrategy(path_pattern=f"{tmpdirname}/*", enable_global_documents=True)

        files = [file async for file in local_list_strategy.list()]
        assert len(files) == 3
        for file in files:
            assert file.acls == {"oids": ["all"], "groups": ["all"]}
            file.close()
