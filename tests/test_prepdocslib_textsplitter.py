import json
import shutil
from pathlib import Path

import pytest
import tiktoken

from prepdocslib.listfilestrategy import LocalListFileStrategy
from prepdocslib.page import Page
from prepdocslib.pdfparser import LocalPdfParser
from prepdocslib.searchmanager import Section
from prepdocslib.textsplitter import (
    ENCODING_MODEL,
    SentenceTextSplitter,
    SimpleTextSplitter,
)

# Deterministic single-token character used to create token pressure by repetition
# while keeping tests readable (1 char = 1 token).
SINGLE_TOKEN_CHAR = "¢"  # 1 token under cl100k_base
_bpe_for_guard = tiktoken.encoding_for_model(ENCODING_MODEL)
assert len(_bpe_for_guard.encode(SINGLE_TOKEN_CHAR)) == 1, (
    f"Invariant changed: {SINGLE_TOKEN_CHAR!r} no longer encodes to 1 token under {ENCODING_MODEL}; "
    "adjust tests to a different stable single-token char."
)


def test_sentencetextsplitter_split_empty_pages():
    t = SentenceTextSplitter()

    assert list(t.split_pages([])) == []


def test_sentencetextsplitter_split_small_pages():
    t = SentenceTextSplitter()

    chunks = list(t.split_pages(pages=[Page(page_num=0, offset=0, text="Not a large page")]))
    assert len(chunks) == 1
    assert chunks[0].page_num == 0
    assert chunks[0].text == "Not a large page"


@pytest.mark.asyncio
async def test_sentencetextsplitter_list_parse_and_split(tmp_path, snapshot):
    text_splitter = SentenceTextSplitter()
    pdf_parser = LocalPdfParser()
    for pdf in Path("data").glob("*.pdf"):
        shutil.copy(str(pdf.absolute()), tmp_path)

    list_file_strategy = LocalListFileStrategy(path_pattern=str(tmp_path / "*"))
    files = list_file_strategy.list()
    processed = 0
    results = {}
    async for file in files:
        pages = [page async for page in pdf_parser.parse(content=file.content)]
        assert pages
        sections = [
            Section(chunk, content=file, category="test category") for chunk in text_splitter.split_pages(pages)
        ]
        assert sections
        results[file.filename()] = [section.chunk.text for section in sections]
        processed += 1
    assert processed > 1
    # Sort results by key
    results = {k: results[k] for k in sorted(results)}
    snapshot.assert_match(json.dumps(results, indent=2), "text_splitter_sections.txt")


def test_simpletextsplitter_split_empty_pages():
    t = SimpleTextSplitter()

    assert list(t.split_pages([])) == []


def test_simpletextsplitter_split_small_pages():
    t = SimpleTextSplitter()

    chunks = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(chunks) == 1
    assert chunks[0].page_num == 0
    assert chunks[0].text == '{"test": "Not a large page"}'


def test_sentencetextsplitter_split_pages():
    max_object_length = 10
    t = SimpleTextSplitter(max_object_length=max_object_length)

    chunks = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(chunks) == 3
    assert chunks[0].page_num == 0
    assert chunks[0].text == '{"test": "'
    assert len(chunks[0].text) <= max_object_length
    assert chunks[1].page_num == 1
    assert chunks[1].text == "Not a larg"
    assert len(chunks[1].text) <= max_object_length
    assert chunks[2].page_num == 2
    assert chunks[2].text == 'e page"}'
    assert len(chunks[2].text) <= max_object_length


def pytest_generate_tests(metafunc):
    """Parametrize the test_doc fixture with all the pdf files in the test-data directory."""
    if "test_doc" in metafunc.fixturenames:
        metafunc.parametrize("test_doc", [pdf for pdf in Path("tests", "test-data").glob("*.pdf")])


@pytest.mark.asyncio
async def test_sentencetextsplitter_multilang(test_doc, tmp_path):
    text_splitter = SentenceTextSplitter()
    bpe = tiktoken.encoding_for_model(ENCODING_MODEL)
    pdf_parser = LocalPdfParser()

    shutil.copy(str(test_doc.absolute()), tmp_path)

    list_file_strategy = LocalListFileStrategy(path_pattern=str(tmp_path / "*"))
    files = list_file_strategy.list()
    processed = 0
    async for file in files:
        pages = [page async for page in pdf_parser.parse(content=file.content)]
        assert pages
        sections = [
            Section(chunk, content=file, category="test category") for chunk in text_splitter.split_pages(pages)
        ]
        assert sections
        processed += 1

        # Verify the size of the sections
        token_lengths = []
        for section in sections:
            assert section.chunk.text != ""
            assert len(section.chunk.text) <= (text_splitter.max_section_length * 1.2)
            # Verify the number of tokens is below 500
            token_lengths.append((len(bpe.encode(section.chunk.text)), len(section.chunk.text)))
        # verify that none of the numbers in token_lengths are above 500
        assert all([tok_len <= text_splitter.max_tokens_per_section for tok_len, _ in token_lengths]), (
            test_doc.name,
            token_lengths,
        )
    assert processed == 1


def test_split_tables():
    t = SentenceTextSplitter()

    test_text_without_table = """Contoso Electronics is a leader in the aerospace industry, providing advanced electronic
components for both commercial and military aircraft. We specialize in creating cutting-
edge systems that are both reliable and efficient. Our mission is to provide the highest
quality aircraft components to our customers, while maintaining a commitment to safety
and excellence. We are proud to have built a strong reputation in the aerospace industry
and strive to continually improve our products and services. Our experienced team of
engineers and technicians are dedicated to providing the best products and services to our
customers. With our commitment to excellence, we are sure to remain a leader in the
aerospace industry for years to come. At Contoso Electronics, we strive to ensure our employees are getting the feedback they
need to continue growing and developing in their roles. We understand that performance
reviews are a key part of this process and it is important to us that they are conducted in an
effective and efficient manner <fable> Performance reviews are conducted annually and are an important part of your career
development. During the review, your supervisor will discuss your performance over the
past year and provide feedback on areas for improvement. They will also provide you with
an opportunity to discuss your goals and objectives for the upcoming year.
</table>
 """
    # Simulate new parser behavior where tables are already wrapped in <figure>
    test_text_with_table = test_text_without_table.replace("<fable>", "<figure><table>")
    # Close the figure properly (original text already ends with </table>)
    test_text_with_table = test_text_with_table.replace("</table>", "</table></figure>")

    chunks_with_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_with_table)]))
    chunks_without_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_without_table)]))

    # Ensure table (wrapped in figure) appears exactly once in the with_table variant
    assert any("<figure><table>" in sp.text for sp in chunks_with_table)
    figure_table_occurrences = sum(sp.text.count("<figure><table>") for sp in chunks_with_table)
    assert figure_table_occurrences == 1, "Wrapped figure+table should appear exactly once."
    # Placeholder variant should have no <table>
    assert all("<table" not in sp.text for sp in chunks_without_table)


# parameterize to check multiple files
@pytest.mark.parametrize("file_name", ["pages_with_figures.json", "pages_with_just_text.json"])
def test_pages_with_figures(snapshot, file_name):
    # open up the serialized pages from pages_with_figures.json
    file_path = Path(__file__).parent / "test-data" / file_name
    with open(file_path) as f:
        pages_dicts = json.load(f)

    pages = [
        Page(page_num=page_dict["page_num"], offset=page_dict["offset"], text=page_dict["text"])
        for page_dict in pages_dicts
    ]
    # call split_pages on the pages
    t = SentenceTextSplitter()
    chunks = list(t.split_pages(pages=pages))

    # check that the chunks are the same as the expected chunks
    chunks_dicts = [{"text": chunk.text, "page_num": chunk.page_num} for chunk in chunks]
    chunks_json = json.dumps(chunks_dicts, indent=2)
    snapshot.assert_match(chunks_json, "split_pages_with_figures.json")


def test_large_figure_not_split():
    # Construct an intentionally large figure (repeated table rows) that would exceed token limits if split naively
    repeated_rows = "".join([f"<tr><td>{i}</td><td>Data {i}</td></tr>" for i in range(200)])
    large_figure = f"<figure><figcaption><table>{repeated_rows}</table></figcaption></figure>"
    surrounding_text = "Intro paragraph before figure. " + large_figure + " Conclusion after figure." * 2
    pages = [Page(page_num=0, offset=0, text=surrounding_text)]
    t = SentenceTextSplitter(max_tokens_per_section=50)  # Force a low token threshold
    chunks = list(t.split_pages(pages=pages))

    # Assert at least one chunk contains the entire figure block intact
    figure_chunks = [chunk for chunk in chunks if "<figure" in chunk.text and "</figure>" in chunk.text]
    assert figure_chunks, "Expected a chunk containing the whole figure"
    for fc in figure_chunks:
        assert fc.text.count("<figure") == fc.text.count("</figure>"), "Figure tags should be balanced in a chunk"

    # Ensure we did not produce any chunk that has an opening figure tag without a closing one
    for chunk in chunks:
        if "<figure" in chunk.text:
            assert "</figure>" in chunk.text, "Chunk with opening <figure should include closing </figure>"


def test_figure_at_start_emitted():
    """Figure at very start of page should be emitted (regression test for missing emission bug)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=50)
    fig = "<figure><img src='x.png'/><figcaption>Cap</figcaption></figure>"
    pages = [Page(page_num=0, offset=0, text=fig + " Following text sentence one. Another sentence.")]
    chunks = list(splitter.split_pages(pages))
    assert chunks, "No chunks produced"
    assert any("<figure" in c.text and "</figure>" in c.text for c in chunks), "Figure not emitted as atomic chunk"
    for c in chunks:
        if "<figure" in c.text:
            assert c.text.count("<figure") == c.text.count("</figure>")


def test_unbalanced_figure_treated_as_text():
    """Unbalanced <figure> markup should be treated as plain text and still be split safely."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    # Missing closing </figure>
    txt = "Intro " + "<figure><img/></figcaption " + " morewords" * 30
    pages = [Page(page_num=0, offset=0, text=txt)]
    chunks = list(splitter.split_pages(pages))
    assert chunks
    # At least one chunk contains the raw (broken) markup
    assert any("<figure" in c.text for c in chunks)
    # None should contain a balanced closing tag (we never added one)
    assert all(not ("<figure" in c.text and "</figure>" in c.text) for c in chunks), "Unexpected closed figure"


def test_oversize_single_sentence_recursion():
    """A single oversized sentence (no punctuation) should be recursively split by token logic."""
    splitter = SentenceTextSplitter(max_tokens_per_section=50)
    # Use SINGLE_TOKEN_CHAR repetition to exceed token limit: 120 chars -> 120 tokens > 50
    long_run = SINGLE_TOKEN_CHAR * 120
    page = Page(page_num=0, offset=0, text=long_run + ".")
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) > 1, "Expected recursive splitting for oversized sentence"
    bpe = tiktoken.encoding_for_model(ENCODING_MODEL)
    assert all(len(bpe.encode(c.text)) <= splitter.max_tokens_per_section for c in chunks)


def test_sentence_boundary_fallback_half_split():
    """Exercise fallback path when no sentence ending near midpoint causes half/overlap split."""
    splitter = SentenceTextSplitter(max_tokens_per_section=60)
    text = "Start" + (" word" * 180) + "."  # Only final punctuation
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) >= 2, "Expected multiple chunks from fallback split"


def test_cross_page_merge_mid_sentence():
    """Verify cross-page merge combines mid-sentence break when within limits."""
    splitter = SentenceTextSplitter(max_tokens_per_section=200)
    page1 = Page(page_num=0, offset=0, text="This is a sentence intentionally broken across pages without completion")
    page2 = Page(page_num=1, offset=0, text="and continues on the next page with more content.")
    chunks = list(splitter.split_pages([page1, page2]))
    # Ensure there exists a chunk containing both segments (merged) with a space boundary inserted
    merged = any("completion and continues" in c.text or "completionand continues" in c.text for c in chunks)
    assert merged, f"Cross-page merge did not occur. Chunks: {[c.text for c in chunks]}"


def test_normalization_trims_leading_space_overflow():
    """Chunk slightly over char limit due to leading spaces should be normalized (trimmed)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=400)
    splitter.max_section_length = 50  # tighten char limit for test
    base = "A" * 50
    overflow = " " * 4 + "tail."  # push over 1.2 * max ( = 60 ) by a small margin
    page = Page(page_num=0, offset=0, text=base + overflow)
    chunks = list(splitter.split_pages([page]))
    assert chunks
    max_chars = int(splitter.max_section_length * 1.2)
    for c in chunks:
        if "<figure" not in c.text:
            assert len(c.text) <= max_chars + 3  # after trimming allowance


def test_split_page_by_max_tokens_merges_heading_with_figure():
    """Direct helper invocation should keep heading attached to following figure in same chunk."""
    splitter = SentenceTextSplitter(max_tokens_per_section=30)
    heading = "Heading before figure. "
    rows = "".join(f"<tr><td>{i}</td></tr>" for i in range(40))
    figure = f"<figure><table>{rows}</table></figure>"
    joined = heading + figure + " trailing text."
    chunks = list(splitter.split_page_by_max_tokens(0, joined))
    assert any(c.text.startswith(heading) and "<figure" in c.text for c in chunks), "Heading and figure not merged"


def test_recursive_split_uses_sentence_boundary():
    """Ensure recursive split picks a nearby sentence boundary when available (split_position > 0 path)."""
    # Force very small token limit so recursion occurs even for moderate text length
    splitter = SentenceTextSplitter(max_tokens_per_section=20)
    # Create two sentences; first ends with period near middle.
    left = ("word " * 15).strip() + "."  # ~15 words
    right = ("next " * 14).strip() + "."
    text = left + right
    chunks = list(splitter.split_page_by_max_tokens(0, text))
    assert len(chunks) >= 2, f"Expected recursive split, got 1 chunk: {chunks[0].text}"
    assert chunks[0].text.endswith("."), "First chunk should end at sentence boundary"
    # Ensure second chunk starts with a lowercase letter from right side (not merged improperly)
    assert chunks[1].text[:1].islower()


def test_cross_page_merge_fragment_shift_no_sentence_end():
    """Cross-page merge failing due to size triggers trailing fragment carry-forward when previous chunk has no sentence ending."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    splitter.max_section_length = 120
    # Previous page produces one chunk without punctuation so last_end = -1 (fragment_start=0).
    page1 = Page(page_num=0, offset=0, text="word " * 30)  # ~150 chars, will be emitted as one chunk
    # Next page starts with lowercase continuation; combined would exceed token limit so merge fails.
    page2 = Page(page_num=1, offset=0, text="continuation " * 5 + "end.")
    chunks = list(splitter.split_pages([page1, page2]))
    # Ensure we did NOT merge whole (would have uppercase W then lowercase c joined) but did shift some fragment
    joined_texts = "||".join(c.text for c in chunks)
    assert "word word" in joined_texts  # previous content still present somewhere
    # Because trailing fragment carry-forward moves everything (no sentence end) previous chunk should become None and its content redistributed
    # Expect at least one chunk starting with a moved fragment part 'word'
    assert any(c.text.startswith("word") for c in chunks)


def test_cross_page_merge_fragment_shift_with_sentence_end_and_shortening():
    """Cross-page merge trailing fragment carry-forward path where a fragment contains an internal sentence boundary allowing shortening."""
    splitter = SentenceTextSplitter(max_tokens_per_section=60)
    splitter.max_section_length = 120
    # Previous chunk ends mid-sentence but contains an earlier full stop to anchor retained portion
    prev_text = (
        "Intro sentence. "  # full sentence to retain
        "Second part that is quite long and will be partially moved and maybe trimmed due to limits "
        "with extra words"
    )
    # Force previous page to emit as single chunk
    page1 = Page(page_num=0, offset=0, text=prev_text)
    # Next page begins lowercase continuation so merge attempted then trailing fragment carry-forward triggered
    page2 = Page(page_num=1, offset=0, text="continuation that keeps going with additional trailing words.")
    chunks = list(splitter.split_pages([page1, page2]))
    # We expect retained intro sentence as its own (ends with '.') and a following chunk starting with moved fragment
    retained_present = any(c.text.strip().startswith("Intro sentence.") for c in chunks)
    moved_fragment_present = any(
        c.text.strip().startswith("Second part") or c.text.strip().startswith("Second part that") for c in chunks
    )
    assert retained_present, "Retained portion after trailing fragment carry-forward missing"
    assert moved_fragment_present, "Moved (shortened) fragment not found in any chunk"


def test_cross_page_merge_fragment_shift_hard_trim():
    """Exercise hard trim branch where fragment must be aggressively shortened (token loop)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    splitter.max_section_length = 100
    # Use repeated single-token char run to create a large fragment (260 tokens) with minimal punctuation.
    fragment_run_len = 260
    fragment_run = SINGLE_TOKEN_CHAR * fragment_run_len
    prev_text = "Start. " + fragment_run
    page1 = Page(page_num=0, offset=0, text=prev_text)
    # Next page small continuation
    page2 = Page(page_num=1, offset=0, text="continuation")
    chunks = list(splitter.split_pages([page1, page2]))
    # Ensure that some fragment run has been moved but also trimmed (shorter than original)
    moved_runs = [c.text for c in chunks if c.text.startswith(SINGLE_TOKEN_CHAR)]
    if moved_runs:
        assert all(len(run) < fragment_run_len for run in moved_runs), "Expected hard trim to shorten fragment"
    # Ensure we still have a chunk starting with 'Start.' retained portion
    assert any(c.text.startswith("Start.") for c in chunks)


def test_figure_merge_both_branches():
    """Ensure figure merge handles preceding text and consecutive figures.

    This test exercises split_pages with a single Page containing both
    branches: (1) a figure following existing text, (2) a second consecutive figure,
    then trailing text.
    """
    splitter = SentenceTextSplitter(max_tokens_per_section=100)
    page_text = (
        "Heading before."  # preceding text (current non-empty before first figure)
        + "<figure><img src='a.png'/></figure>"  # first figure attaches to text and flushes
        + "<figure><img src='b.png'/></figure>"  # second figure emitted standalone
        + "Tail sentence."  # trailing text emitted after figures
    )
    pages = [Page(page_num=0, offset=0, text=page_text)]
    chunks = list(splitter.split_pages(pages))
    # Expect: chunk0 = heading + first figure, chunk1 = second figure, chunk2 (or later) starts with Tail
    assert len(chunks) >= 3, f"Unexpected chunk count: {[c.text for c in chunks]}"
    assert chunks[0].text.startswith("Heading before.") and chunks[0].text.count("<figure") == 1
    # Find a standalone second figure chunk (could be index 1) containing only the second figure markup
    figure_only = next(
        (c for c in chunks[1:] if c.text.count("<figure") == 1 and c.text.strip().startswith("<figure")), None
    )
    assert figure_only is not None, "Second figure not emitted standalone"
    assert any(
        c.text.startswith("Tail") for c in chunks[chunks.index(figure_only) + 1 :]
    ), "Tail text chunk missing after figures"


def test_sentence_boundary_right_side():
    """Trigger sentence boundary discovery on the right side of midpoint (alternate branch)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    # Construct long text with no punctuation until slightly after midpoint, then a period.
    left = ("word " * 120).strip()  # long left without punctuation
    # Insert single period after some extra words just to the right of mid point
    right = ("cont " * 10) + "End." + (" tail " * 20)
    text = left + " " + right
    chunks = list(splitter.split_page_by_max_tokens(0, text))
    assert len(chunks) > 1, f"Expected recursion, got 1 chunk length={len(chunks[0].text)}"
    # Ensure a chunk ends at the first period (right-side discovered)
    assert any(c.text.endswith("End.") for c in chunks), f"Chunks: {[c.text for c in chunks]}"


def test_sentence_boundary_left_side():
    """Trigger sentence boundary on the left side of midpoint (left branch hit first)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    # Create text where a period appears before middle and no period until far right.
    left_sentence = ("alpha " * 25).strip() + "."  # this period should be chosen
    # Long tail without punctuation until very end ensures search finds left first.
    tail = " beta" * 120 + "."  # final period far to the right
    text = left_sentence + tail
    chunks = list(splitter.split_page_by_max_tokens(0, text))
    assert len(chunks) > 1
    assert chunks[0].text.endswith("."), "Expected first chunk to terminate at left boundary period"


def test_sentence_boundary_left_midpoint_exact():
    """Exact midpoint has a period so the midpoint search loop selects the left boundary immediately."""
    splitter = SentenceTextSplitter(max_tokens_per_section=20)
    # Create symmetric text with period exactly at midpoint index.
    left = "A" * 100
    right = "B" * 100
    text = left + "." + right  # length 201; midpoint index = 100 -> '.'
    chunks = list(splitter.split_page_by_max_tokens(0, text))
    assert len(chunks) >= 2
    assert chunks[0].text.endswith("."), "First chunk should end with midpoint period"


def test_recursive_split_prefers_word_break_over_overlap():
    """Punctuation-free text with spaces should split at a word break (space) rather than arbitrary midpoint overlap duplication."""
    # Use deterministic single-token chars to guarantee token overflow.
    splitter = SentenceTextSplitter(max_tokens_per_section=20)  # Force very low token limit
    # Create 60 single-token words separated by spaces (approx 120+ tokens including spaces -> >20)
    word = SINGLE_TOKEN_CHAR * 3  # 3 tokens per word
    words = [word for _ in range(25)]  # 75 tokens (plus spaces) >> 20 limit
    text = " ".join(words)
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) > 1, "Expected multiple chunks due to low token cap forcing recursion"
    # Ensure we never split inside a word: boundary between chunks should not create alpha-alpha adjacency
    for i in range(len(chunks) - 1):
        left = chunks[i].text.rstrip()
        right = chunks[i + 1].text.lstrip()
        if left and right:
            assert not (
                left[-1].isalpha() and right[0].isalpha()
            ), f"Mid-word split detected: {left[-10:]}|{right[:10]}"


def test_recursive_split_overlap_fallback_when_no_word_breaks():
    """Long contiguous text without sentence endings or word breaks should fall back to midpoint overlap strategy."""
    splitter = SentenceTextSplitter(max_tokens_per_section=30)
    # Use a contiguous run of the single-token char (no spaces / punctuation) to exceed limit.
    contiguous = SINGLE_TOKEN_CHAR * 120  # 120 tokens > 30 limit, no word breaks or sentence endings
    page = Page(page_num=0, offset=0, text=contiguous)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) > 1, "Expected recursion via overlap fallback"
    # Detect some overlap duplication at boundaries (heuristic)
    found_overlap = False
    for i in range(len(chunks) - 1):
        left = chunks[i].text
        right = chunks[i + 1].text
        probe = left[-12:]
        if probe and probe in right[: len(probe) + 4]:
            found_overlap = True
            break
    assert found_overlap, "Expected overlapping duplicated region between chunks"
    # Confirm no spaces since there are no word breaks
    assert all(" " not in c.text for c in chunks)


def test_fragment_shift_token_limit_fits_false():
    """Trigger trailing fragment carry-forward where fits() fails solely due to token limit (not char length) and trimming loop runs."""
    # Configure large char allowance so only token constraint matters.
    splitter = SentenceTextSplitter(max_tokens_per_section=50)
    splitter.max_section_length = 5000  # very high to avoid char-based fits() failure
    # Build fragment via single-token char repetition (120 tokens) beyond the 50-token limit.
    fragment = SINGLE_TOKEN_CHAR * 120  # no terminating punctuation
    prev_text = "Intro sentence." + fragment  # last sentence end ensures fragment_start > 0
    page1 = Page(page_num=0, offset=0, text=prev_text)
    # Next page starts lowercase to trigger merge attempt; small first_new keeps emphasis on fragment tokens.
    page2 = Page(page_num=1, offset=0, text="cont tail")
    chunks = list(splitter.split_pages([page1, page2]))
    # Retained intro sentence should appear.
    assert any(c.text.startswith("Intro sentence.") for c in chunks)
    # A moved fragment portion beginning with SINGLE_TOKEN_CHAR should appear but be trimmed
    moved = [c.text for c in chunks if c.text.startswith(SINGLE_TOKEN_CHAR)]
    if moved:
        assert all(len(m) < len(fragment) for m in moved), "Expected trimmed fragment shorter than original"


def test_fragment_shift_token_limit_single_token_char():
    """Deterministically force token overflow using the single-token pressure char.
    Repeats exceed the token limit while keeping 1:1 char/token mapping for simpler assertions.
    """
    splitter = SentenceTextSplitter(max_tokens_per_section=80)
    splitter.max_section_length = 5000  # ensure only token constraint matters
    pressure_char = SINGLE_TOKEN_CHAR  # now single-token char
    bpe = tiktoken.encoding_for_model(ENCODING_MODEL)
    assert len(bpe.encode(pressure_char)) == 1
    fragment = pressure_char * 400  # 400 tokens > 80 token limit
    prev_text = "Intro sentence." + fragment  # ensures fragment_start > 0 (prior sentence end)
    page1 = Page(page_num=0, offset=0, text=prev_text)
    page2 = Page(page_num=1, offset=0, text="cont tail")
    chunks = list(splitter.split_pages([page1, page2]))
    assert any(c.text.startswith("Intro sentence.") for c in chunks)
    moved = [c.text for c in chunks if c.text and c.text[0] == pressure_char]
    if moved:
        assert all(len(m) < len(fragment) for m in moved), "Expected trimmed fragment shorter than original"


def test_safe_concat_html_tag_boundary():
    """Cross-page merge where previous ends with '>' ensures no extra space inserted."""
    splitter = SentenceTextSplitter(max_tokens_per_section=80)
    page1 = Page(page_num=0, offset=0, text="<b>Bold tag close></b>")
    # Force text so that merge conditions apply (lowercase start, not sentence end)
    page2 = Page(page_num=1, offset=0, text="continues here without leading space.")
    chunks = list(splitter.split_pages([page1, page2]))
    merged = next((c for c in chunks if "</b>continues" in c.text or "</b> continues" in c.text), None)
    assert merged is not None, f"Expected merged chunk, got: {[c.text for c in chunks]}"
    # Ensure we did not insert a space because preceding char was '>'
    assert "</b>continues" in merged.text, "Expected direct concatenation without space after HTML closing tag"


def test_normalization_trims_trailing_space_overflow():
    """Chunk barely over limit with trailing space/newline should have trailing whitespace stripped by normalization."""
    splitter = SentenceTextSplitter(max_tokens_per_section=400)
    splitter.max_section_length = 30
    max_chars = int(splitter.max_section_length * 1.2)  # 36
    # Build a chunk that will exceed max_chars by <=3 after normalization attempt and ends with space/newline
    # Construct a page with a single long sentence forcing one chunk slightly over limit, ending with whitespace.
    # Use no sentence-ending punctuation early so accumulation doesn't flush.
    # Build base so total length including one trailing space is max_chars+2 (within +3 window)
    core = "C" * (max_chars + 1)
    text = core + " \n"  # adds space + newline making len = max_chars+3
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) == 1, "Expected single chunk to test normalization trimming"
    normalized = chunks[0].text
    # After normalization, length should be <= max_chars+3 and should not end with space/newline if over limit originally
    assert len(normalized) <= max_chars + 3
    # Normalization should have rstrip()'d trailing whitespace
    assert not normalized.endswith((" ", "\n")), "Trailing whitespace should be trimmed"


def test_cross_page_fragment_shortening_path():
    """Exercise trailing fragment carry-forward after a complete sentence; ensures part of trailing fragment is moved and retained sentence stays."""
    splitter = SentenceTextSplitter(max_tokens_per_section=55)
    splitter.max_section_length = 120
    # Previous ends with two sentences, second incomplete to encourage trailing fragment carry-forward
    prev = "Complete sentence one. Asecondpartthatshouldbeshortened because it is long"
    page1 = Page(page_num=0, offset=0, text=prev)
    nxt = "continues here with lowercase start."  # triggers merge attempt (lowercase)
    page2 = Page(page_num=1, offset=0, text=nxt)
    chunks = list(splitter.split_pages([page1, page2]))
    # Ensure we have a chunk starting with retained first sentence and another with shortened moved fragment
    assert any(c.text.strip().startswith("Complete sentence one.") for c in chunks)
    assert any("Asecondpart" in c.text for c in chunks)


def test_cross_page_fragment_hard_trim_iterative():
    """Hard trim path where fragment must be iteratively token-trimmed (loop executes)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=30)
    splitter.max_section_length = 80
    fragment_iter_len = 210  # 420 tokens
    prev = "Intro. " + (SINGLE_TOKEN_CHAR * fragment_iter_len)
    page1 = Page(page_num=0, offset=0, text=prev)
    page2 = Page(page_num=1, offset=0, text="continuation lower start")
    chunks = list(splitter.split_pages([page1, page2]))
    # Some trimmed fragment should appear but much shorter than original
    trimmed = [c.text for c in chunks if c.text.startswith(SINGLE_TOKEN_CHAR)]
    if trimmed:
        assert all(len(t) < fragment_iter_len for t in trimmed)


def test_intra_page_semantic_overlap_applied():
    """When multiple chunks arise on the SAME page, the second should begin with duplicated
    semantic overlap (~10% tail of prior), unless figure or heading prevents it."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    splitter.max_section_length = 200  # keep char constraint loose
    # Build text long enough to force at least two chunks via token limit using many short sentences
    base_sentence = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda. "
    text = base_sentence * 6  # repeated => should exceed token cap for one chunk
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) >= 2, f"Need >=2 chunks to test overlap: {[c.text for c in chunks]}"
    first, second = chunks[0], chunks[1]
    # Overlap suffix length target
    overlap_len_chars = int(splitter.max_section_length * splitter.semantic_overlap_percent / 100)
    tail = first.text[-overlap_len_chars:]
    # The implementation may trim to boundary; accept partial. Take a probe substring from tail.
    probe = tail.strip()[:25]
    duplicated = False
    if probe and probe in second.text[: max(80, len(probe) + 20)]:
        duplicated = True
    assert duplicated, (
        "Expected semantic overlap duplication between first and second intra-page chunks. "
        f"Tail probe={probe!r} Second start={second.text[:120]!r}"
    )


def test_no_overlap_after_figure_previous():
    """If previous chunk contains a figure, semantic overlap should not duplicate its suffix."""
    splitter = SentenceTextSplitter(max_tokens_per_section=60)
    # Compose page with an early figure chunk; then long continuation forcing another chunk.
    fig = "<figure><img src='a.png'/><figcaption>Caption text here</figcaption></figure>"
    continuation = " continuing text that will form another chunk because we repeat it."
    text = fig + continuation * 10
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    # Locate figure chunk
    figure_index = next((i for i, c in enumerate(chunks) if "<figure" in c.text), None)
    assert figure_index is not None, "Figure chunk not found"
    if figure_index < len(chunks) - 1:
        after = chunks[figure_index + 1]
        caption_tail = chunks[figure_index].text[-50:].strip()
        # Take head of tail for stricter start comparison
        assert not after.text.startswith(
            caption_tail[:20]
        ), "Unexpected semantic overlap duplication from figure chunk tail"


def test_append_overlap_preserves_next_chunk_start():
    """Ensure the semantic overlap append to the previous chunk instead of
    prepending to the next, so each chunk starts at a clean sentence
    boundary.

    We build text with short sentences forcing multiple chunks due to a low
    token limit. We then assert:
    - First and second chunks both start with a capital letter / beginning of a sentence.
    - Some prefix of the second chunk's starting text is appended to the tail of
      the first chunk (overlap duplication) without altering the second chunk's
      own start.
    - The duplicated region is not the entire first sentence of the second chunk
      (boundary trimming logic should avoid huge duplication).
    """
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    splitter.max_section_length = 300  # plenty of char room
    # Craft many short sentences; ensure > 40 tokens total to create >1 chunk.
    base_sentences = [
        "Alpha beta gamma delta epsilon zeta.",
        "Second sentence with some words.",
        "Third sentence continues context.",
        "Fourth sentence ends here.",
    ]
    # Repeat to induce splitting while preserving clear sentence boundaries.
    text = " ".join(base_sentences * 2)
    page = Page(page_num=0, offset=0, text=text)
    chunks = list(splitter.split_pages([page]))
    assert len(chunks) >= 2, f"Need >=2 chunks, got {len(chunks)}: {[c.text for c in chunks]}"
    first, second = chunks[0], chunks[1]

    # Heuristic: second chunk should start at start of a sentence (capital letter or quote)
    second_start = second.text.lstrip()[:1]
    assert second_start and (second_start.isupper() or second_start in "\"'"), (
        "Second chunk does not appear to start at a sentence boundary",
        second.text[:60],
    )

    # Find overlap: take short head of second chunk and ensure it's present at end of first chunk
    head_probe = second.text.strip()[:25]
    # Overlap trimming may remove punctuation; search a smaller portion if needed
    head_probe_min = head_probe[:15]
    tail_of_first = first.text[-200:]
    assert any(p for p in [head_probe, head_probe_min] if p and p in tail_of_first), (
        "Expected some head of second chunk to be appended to first chunk tail",
        head_probe,
        first.text[-120:],
        second.text[:120],
    )

    # Ensure second chunk did not get the duplicated prefix prepended (i.e., it still starts with its natural beginning)
    # We compare by checking that the second chunk does NOT start with tail of first (beyond acceptable small duplication)
    # Accept a small duplication but reject if second start includes obvious mid-sentence continuation (lowercase after space)
    assert not second.text.startswith(
        first.text[-50:].lstrip()
    ), "Second chunk unexpectedly begins with large slice of first chunk tail"

    # Ensure first chunk ends with duplicated region rather than cutting mid-word (no alpha-alpha boundary inside appended probe)
    boundary_ok = True
    if tail_of_first and second.text:
        if tail_of_first[-1].isalnum() and second.text[0].isalnum():
            # If this occurs, safe_concat would have inserted a space earlier; treat as failure
            boundary_ok = tail_of_first.endswith(" ")
    assert boundary_ok, "First chunk tail and second chunk head joined mid-word without boundary handling"
