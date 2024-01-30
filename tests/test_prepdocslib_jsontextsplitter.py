from scripts.prepdocslib.page import Page
from scripts.prepdocslib.textsplitter import SimpleTextSplitter


def test_json_split_empty_pages():
    t = SimpleTextSplitter(True)

    assert list(t.split_pages([])) == []


def test_json_split_small_pages():
    t = SimpleTextSplitter(verbose=True)

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == '{"test": "Not a large page"}'


def test_json_split_pages():
    max_object_length = 10
    t = SimpleTextSplitter(max_object_length=max_object_length, verbose=True)

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(split_pages) == 3
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == '{"test": "'
    assert len(split_pages[0].text) <= max_object_length
    assert split_pages[1].page_num == 1
    assert split_pages[1].text == "Not a larg"
    assert len(split_pages[1].text) <= max_object_length
    assert split_pages[2].page_num == 2
    assert split_pages[2].text == 'e page"}'
    assert len(split_pages[2].text) <= max_object_length
