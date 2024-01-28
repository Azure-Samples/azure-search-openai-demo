import io

from scripts.prepdocslib.jsonparser import JsonParser


def test_jsonparser_single_obj():
    file = io.StringIO('{"test": "test"}')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page for page in jsonparser.parse(file)]
    assert len(pages) == 1


def test_jsonparser_array_multiple_obj():
    file = io.StringIO('[{"test": "test"},{"test": "test"}]')
    file.name = "test.json"
    jsonparser = JsonParser()
    pages = [page for page in jsonparser.parse(file)]
    assert len(pages) == 2
