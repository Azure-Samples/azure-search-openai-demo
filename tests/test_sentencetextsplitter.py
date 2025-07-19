from unittest.mock import patch

import pytest

from prepdocslib.textsplitter import SentenceTextSplitter


@pytest.mark.parametrize(
    "actual_percentage, expected_section_overlap",
    [
        (100, 1000),
        (80, 800),
        (10.75, 107),
        (10, 100),
        (0, 0),
    ],
)
def test_sentence_text_splitter_initializes_overlap_correctly(
    actual_percentage: float, expected_section_overlap: float
):
    with patch("prepdocslib.textsplitter.DEFAULT_OVERLAP_PERCENT", actual_percentage):
        subject = SentenceTextSplitter(False)
        assert subject.section_overlap == expected_section_overlap
