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

# Multi-token deterministic character (2 tokens in current model) used to create
# token pressure without excessive string length. Guard at import time so failures
# surface clearly if tokenizer behavior changes.
TWO_TOKEN_CHAR = "Ѐ"
_bpe_for_guard = tiktoken.encoding_for_model(ENCODING_MODEL)
assert len(_bpe_for_guard.encode(TWO_TOKEN_CHAR)) == 2, (
    f"Invariant changed: {TWO_TOKEN_CHAR!r} no longer encodes to 2 tokens under {ENCODING_MODEL}; "
    "adjust tests to a different stable multi-token char."
)


def test_sentencetextsplitter_split_empty_pages():
    t = SentenceTextSplitter()

    assert list(t.split_pages([])) == []


def test_sentencetextsplitter_split_small_pages():
    t = SentenceTextSplitter()

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text="Not a large page")]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == "Not a large page"


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
            Section(split_page, content=file, category="test category")
            for split_page in text_splitter.split_pages(pages)
        ]
        assert sections
        results[file.filename()] = [section.split_page.text for section in sections]
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

    split_pages = list(t.split_pages(pages=[Page(page_num=0, offset=0, text='{"test": "Not a large page"}')]))
    assert len(split_pages) == 1
    assert split_pages[0].page_num == 0
    assert split_pages[0].text == '{"test": "Not a large page"}'


def test_sentencetextsplitter_split_pages():
    max_object_length = 10
    t = SimpleTextSplitter(max_object_length=max_object_length)

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
            Section(split_page, content=file, category="test category")
            for split_page in text_splitter.split_pages(pages)
        ]
        assert sections
        processed += 1

        # Verify the size of the sections
        token_lengths = []
        for section in sections:
            assert section.split_page.text != ""
            assert len(section.split_page.text) <= (text_splitter.max_section_length * 1.2)
            # Verify the number of tokens is below 500
            token_lengths.append((len(bpe.encode(section.split_page.text)), len(section.split_page.text)))
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

    split_pages_with_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_with_table)]))
    split_pages_without_table = list(t.split_pages(pages=[Page(page_num=0, offset=0, text=test_text_without_table)]))

    # Ensure table (wrapped in figure) appears exactly once in the with_table variant
    assert any("<figure><table>" in sp.text for sp in split_pages_with_table)
    figure_table_occurrences = sum(sp.text.count("<figure><table>") for sp in split_pages_with_table)
    assert figure_table_occurrences == 1, "Wrapped figure+table should appear exactly once."
    # Placeholder variant should have no <table>
    assert all("<table" not in sp.text for sp in split_pages_without_table)


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
    split_pages = list(t.split_pages(pages=pages))

    # check that the split_pages are the same as the expected split_pages
    split_pages_dicts = [{"text": split_page.text, "page_num": split_page.page_num} for split_page in split_pages]
    split_pages_json = json.dumps(split_pages_dicts, indent=2)
    snapshot.assert_match(split_pages_json, "split_pages_with_figures.json")


def test_large_figure_not_split():
    # Construct an intentionally large figure (repeated table rows) that would exceed token limits if split naively
    repeated_rows = "".join([f"<tr><td>{i}</td><td>Data {i}</td></tr>" for i in range(200)])
    large_figure = f"<figure><figcaption><table>{repeated_rows}</table></figcaption></figure>"
    surrounding_text = "Intro paragraph before figure. " + large_figure + " Conclusion after figure." * 2
    pages = [Page(page_num=0, offset=0, text=surrounding_text)]
    t = SentenceTextSplitter(max_tokens_per_section=50)  # Force a low token threshold
    split_pages = list(t.split_pages(pages=pages))

    # Assert at least one chunk contains the entire figure block intact
    figure_chunks = [sp for sp in split_pages if "<figure" in sp.text and "</figure>" in sp.text]
    assert figure_chunks, "Expected a chunk containing the whole figure"
    for fc in figure_chunks:
        assert fc.text.count("<figure") == fc.text.count("</figure>"), "Figure tags should be balanced in a chunk"

    # Ensure we did not produce any chunk that has an opening figure tag without a closing one
    for sp in split_pages:
        if "<figure" in sp.text:
            assert "</figure>" in sp.text, "Chunk with opening <figure should include closing </figure>"


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
    # Use TWO_TOKEN_CHAR to exceed token limit with fewer characters: 120 chars -> 240 tokens > 50
    long_run = TWO_TOKEN_CHAR * 120
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
    """Cross-page merge failing due to size triggers fragment shift when previous chunk has no sentence ending."""
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
    # Because fragment shift moves everything (no sentence end) previous chunk should become None and its content redistributed
    # Expect at least one chunk starting with a moved fragment part 'word'
    assert any(c.text.startswith("word") for c in chunks)


def test_cross_page_merge_fragment_shift_with_sentence_end_and_shortening():
    """Cross-page merge fragment shift path where a fragment contains an internal sentence boundary allowing shortening."""
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
    # Next page begins lowercase continuation so merge attempted then fragment shift triggered
    page2 = Page(page_num=1, offset=0, text="continuation that keeps going with additional trailing words.")
    chunks = list(splitter.split_pages([page1, page2]))
    # We expect retained intro sentence as its own (ends with '.') and a following chunk starting with moved fragment
    retained_present = any(c.text.strip().startswith("Intro sentence.") for c in chunks)
    moved_fragment_present = any(
        c.text.strip().startswith("Second part") or c.text.strip().startswith("Second part that") for c in chunks
    )
    assert retained_present, "Retained portion after fragment shift missing"
    assert moved_fragment_present, "Moved (shortened) fragment not found in any chunk"


def test_cross_page_merge_fragment_shift_hard_trim():
    """Exercise hard trim branch where fragment must be aggressively shortened (token loop)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=40)
    splitter.max_section_length = 100
    # Use multi-token char run to create a large fragment (260 * 2 = 520 tokens) with minimal punctuation.
    fragment_run_len = 260
    fragment_run = TWO_TOKEN_CHAR * fragment_run_len
    prev_text = "Start. " + fragment_run
    page1 = Page(page_num=0, offset=0, text=prev_text)
    # Next page small continuation
    page2 = Page(page_num=1, offset=0, text="continuation")
    chunks = list(splitter.split_pages([page1, page2]))
    # Ensure that some fragment run has been moved but also trimmed (shorter than original)
    moved_runs = [c.text for c in chunks if c.text.startswith(TWO_TOKEN_CHAR)]
    if moved_runs:
        assert all(len(run) < fragment_run_len for run in moved_runs), "Expected hard trim to shorten fragment"
    # Ensure we still have a chunk starting with 'Start.' retained portion
    assert any(c.text.startswith("Start.") for c in chunks)


def test_figure_merge_both_branches():
    """Ensure figure merge handles preceding text and consecutive figures (branches where current has / lacks text)."""
    splitter = SentenceTextSplitter(max_tokens_per_section=100)
    text = (
        "Heading before."  # preceding text (current non-empty before first figure)
        + "<figure><img src='a.png'/></figure>"  # first figure attaches to text
        + "<figure><img src='b.png'/></figure>"  # second figure with empty current
        + "Tail sentence."
    )
    chunks = list(splitter.split_page_by_max_tokens(0, text))
    # Expect first chunk to contain heading + first figure, second chunk just second figure, third tail text
    assert len(chunks) >= 3
    assert chunks[0].text.startswith("Heading before.") and chunks[0].text.count("<figure") == 1
    assert chunks[1].text.count("<figure") == 1
    assert chunks[2].text.startswith("Tail")


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


def test_fragment_shift_token_limit_fits_false():
    """Trigger fragment shift where fits() fails solely due to token limit (not char length) and trimming loop runs."""
    # Configure large char allowance so only token constraint matters.
    splitter = SentenceTextSplitter(max_tokens_per_section=50)
    splitter.max_section_length = 5000  # very high to avoid char-based fits() failure
    # Build fragment via multi-token char repetition (120 chars -> 240 tokens) beyond the 50-token limit.
    fragment = TWO_TOKEN_CHAR * 120  # no terminating punctuation
    prev_text = "Intro sentence." + fragment  # last sentence end ensures fragment_start > 0
    page1 = Page(page_num=0, offset=0, text=prev_text)
    # Next page starts lowercase to trigger merge attempt; small first_new keeps emphasis on fragment tokens.
    page2 = Page(page_num=1, offset=0, text="cont tail")
    chunks = list(splitter.split_pages([page1, page2]))
    # Retained intro sentence should appear.
    assert any(c.text.startswith("Intro sentence.") for c in chunks)
    # A moved fragment portion beginning with TWO_TOKEN_CHAR should appear but be trimmed
    moved = [c.text for c in chunks if c.text.startswith(TWO_TOKEN_CHAR)]
    if moved:
        assert all(len(m) < len(fragment) for m in moved), "Expected trimmed fragment shorter than original"


def test_fragment_shift_token_limit_multi_token_char():
    """Deterministically force token overflow using a multi‑token Unicode char (Ѐ = 2 tokens per char).
    Repeats of 'Ѐ' rapidly exceed the token limit while keeping char length well below char threshold,
    exercising the fits() token-limit branch and trimming loop without monkeypatching the encoder.
    """
    splitter = SentenceTextSplitter(max_tokens_per_section=80)
    splitter.max_section_length = 5000  # ensure only token constraint matters
    multi_token_char = "Ѐ"  # currently 2 tokens in text-embedding-ada-002
    # Guardrail: fail fast if tokenizer changes and Ѐ stops being 2 tokens (adjust test strategy then)
    bpe = tiktoken.encoding_for_model(ENCODING_MODEL)
    assert len(bpe.encode(multi_token_char)) == 2, (
        f"Invariant changed: 'Ѐ' is {len(bpe.encode(multi_token_char))} tokens for model {ENCODING_MODEL}; "
        "update test strategy (choose a different stable multi-token char)."
    )
    fragment = multi_token_char * 400  # ~800 tokens > 80 token limit
    prev_text = "Intro sentence." + fragment  # ensures fragment_start > 0 (there is a prior sentence end)
    page1 = Page(page_num=0, offset=0, text=prev_text)
    page2 = Page(page_num=1, offset=0, text="cont tail")
    chunks = list(splitter.split_pages([page1, page2]))
    assert any(c.text.startswith("Intro sentence.") for c in chunks)
    moved = [c.text for c in chunks if c.text and c.text[0] == multi_token_char]
    # Trim loop should reduce moved fragment below original full fragment length
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
    """Exercise fragment shift after a complete sentence; ensures part of trailing fragment is moved and retained sentence stays."""
    splitter = SentenceTextSplitter(max_tokens_per_section=55)
    splitter.max_section_length = 120
    # Previous ends with two sentences, second incomplete to encourage fragment shift
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
    prev = "Intro. " + (TWO_TOKEN_CHAR * fragment_iter_len)
    page1 = Page(page_num=0, offset=0, text=prev)
    page2 = Page(page_num=1, offset=0, text="continuation lower start")
    chunks = list(splitter.split_pages([page1, page2]))
    # Some trimmed fragment should appear but much shorter than original
    trimmed = [c.text for c in chunks if c.text.startswith(TWO_TOKEN_CHAR)]
    if trimmed:
        assert all(len(t) < fragment_iter_len for t in trimmed)
