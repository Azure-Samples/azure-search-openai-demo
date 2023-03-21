import os
import io
import glob
from pypdf import PdfReader, PdfWriter
from azure.search.documents.indexes.models import *
MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100

def index_document(folder_path, search_client, blob_container, index,index_client, category=None,verbose=True):
    status = []
    for filename in glob.glob(os.path.join(folder_path, "*")):
        print(f"Indexing {filename} ")
        try:
            pages = PdfReader(filename).pages
            u = upload_blobs(os.path.basename(filename), pages, blob_container, verbose=verbose )
            print(f"Uploading blobs for {filename} -> {u}")
            sections = create_sections(os.path.basename(filename), pages, category, verbose=verbose)
            print(f"Creating sections for {filename} -> {sections}")
            i = index_sections(os.path.basename(filename), sections=sections, search_client=search_client, index=index, index_client= index_client, verbose=verbose)
            print(f"Indexing sections for {filename} -> {i}")
            status.append ({"success": True, "message": "OK", "filename": filename})
        except Exception as e:
            status.append ({"success": False, "message": str(e)})
    return status
    
def blob_name_from_file_page(filename, page):
    return  f"{filename}-{page}.pdf"

def upload_blobs(filename, pages, blob_container, verbose):
    try:
        if not blob_container.exists():
            blob_container.create_container()
        for i in range(len(pages)):
            blob_name = blob_name_from_file_page(filename, i)
            if verbose: print(f"\tUploading blob for page {i} -> {blob_name}")
            f = io.BytesIO()
            writer = PdfWriter()
            writer.add_page(pages[i])
            writer.write(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)
    except Exception as e:
        return {"error": str(e)}

def split_text(pages, verbose):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
    if verbose: print(f"Splitting '{pages}' into sections")

    page_map = []
    offset = 0
    for i, p in enumerate(pages):
        text = p.extract_text()
        page_map.append((i, offset, text))
        offset += len(text)

    def find_page(offset):
        l = len(page_map)
        for i in range(l - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return l - 1

    all_text = "".join(p[2] for p in page_map)
    length = len(all_text)
    start = 0
    end = length
    while start + SECTION_OVERLAP < length:
        last_word = -1
        end = start + MAX_SECTION_LENGTH

        if end > length:
            end = length
        else:
            # Try to find the end of the sentence
            while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                if all_text[end] in WORDS_BREAKS:
                    last_word = end
                end += 1
            if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                end = last_word # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word boundary
        last_word = -1
        while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
            if all_text[start] in WORDS_BREAKS:
                last_word = start
            start -= 1
        if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        yield (all_text[start:end], find_page(start))
        start = end - SECTION_OVERLAP
        
    if start + SECTION_OVERLAP < end:
        yield (all_text[start:end], find_page(start))

def create_sections(filename, pages, category, verbose):
    for i, (section, pagenum) in enumerate(split_text(pages, verbose=verbose)):
        yield {
            "id": f"{filename}-{i}".replace(".", "_").replace(" ", "_"),
            "content": section,
            "category": category,
            "sourcepage": blob_name_from_file_page(filename, pagenum),
            "sourcefile": filename
        }

def create_search_index(index, index_client, verbose):
    if verbose: print(f"Ensuring search index {index} exists")
    if index not in index_client.list_index_names():
        index = SearchIndex(
            name=index,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcepage", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True)
            ],
            semantic_settings=SemanticSettings(
                configurations=[SemanticConfiguration(
                    name='default',
                    prioritized_fields=PrioritizedFields(
                        title_field=None, prioritized_content_fields=[SemanticField(field_name='content')]))])
        )
        if verbose: print(f"Creating {index} search index")
        index_client.create_index(index)
    else:
        if verbose: print(f"Search index {index} already exists")

def index_sections(filename, sections, search_client, index, index_client,verbose):
    create_search_index(index, index_client, verbose=verbose)
    if verbose: print(f"Indexing sections from '{filename}' into search index '{index}'")
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.index_documents(batch=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if verbose: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        if verbose: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
