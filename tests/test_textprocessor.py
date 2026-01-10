from prepdocslib.page import ImageOnPage, Page
from prepdocslib.textprocessor import combine_text_with_figures


def test_combine_text_with_figures_no_description():
    """Test combine_text_with_figures when image has no description."""
    image = ImageOnPage(
        bytes=b"fake",
        bbox=(0, 0, 100, 100),
        filename="test.png",
        page_num=1,
        figure_id="fig_1",
        placeholder="[PLACEHOLDER_fig_1]",
        description=None,
    )

    page = Page(page_num=1, text="Some text [PLACEHOLDER_fig_1] more text", offset=0)
    page.images = [image]

    # Should keep placeholder when no description
    combine_text_with_figures(page)

    assert "[PLACEHOLDER_fig_1]" in page.text
    assert "<figure>" not in page.text


def test_combine_text_with_figures_placeholder_not_found(caplog):
    """Test combine_text_with_figures when placeholder is not in text."""
    import logging

    image = ImageOnPage(
        bytes=b"fake",
        bbox=(0, 0, 100, 100),
        filename="test.png",
        page_num=1,
        figure_id="fig_1",
        placeholder="[PLACEHOLDER_fig_1]",
        description="A test image",
    )

    page = Page(page_num=1, text="Some text without placeholder", offset=0)
    page.images = [image]

    with caplog.at_level(logging.WARNING):
        combine_text_with_figures(page)

    assert "Placeholder not found for figure fig_1" in caplog.text


def test_combine_text_with_figures_replaces_successfully():
    """Test combine_text_with_figures successfully replaces placeholder."""
    image = ImageOnPage(
        bytes=b"fake",
        bbox=(0, 0, 100, 100),
        filename="test.png",
        page_num=1,
        figure_id="fig_1",
        title="Test Figure",
        placeholder="[PLACEHOLDER_fig_1]",
        description="A test image",
    )

    page = Page(page_num=1, text="Some text [PLACEHOLDER_fig_1] more text", offset=0)
    page.images = [image]

    combine_text_with_figures(page)

    assert "[PLACEHOLDER_fig_1]" not in page.text
    assert "<figure>" in page.text
    assert "A test image" in page.text
