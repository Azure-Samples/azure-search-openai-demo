from prepdocs import filename_to_id

def test_filename_to_id():
    # test ascii filename
    assert filename_to_id("foo.pdf") == "file-foo_pdf-666F6F2E706466"
    # test filename containing unicode
    assert filename_to_id("foo\u00A9.txt") == "file-foo__txt-666F6FC2A92E747874"
    # test filenaming starting with unicode
    assert filename_to_id("ファイル名.pdf") == "file-______pdf-E38395E382A1E382A4E383ABE5908D2E706466"
