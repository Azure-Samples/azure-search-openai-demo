from cgi import FieldStorage
from io import BytesIO
import io
import os
import re
import mimetypes
import tempfile
import time
import logging
import html
import openai
from pypdf import PdfReader, PdfWriter
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from approaches.retrievethenread import RetrieveThenReadApproach
from approaches.readretrieveread import ReadRetrieveReadApproach
from approaches.readdecomposeask import ReadDecomposeAsk
from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
import mimetypes
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer, AudioConfig
from azure.cognitiveservices.speech.audio import AudioInputStream, AudioConfig, AudioStreamFormat
from reportlab.pdfgen import canvas


MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100

# Replace these with your own values, either in environment variables or directly here
AZURE_STORAGE_ACCOUNT = os.environ.get(
    "AZURE_STORAGE_ACCOUNT") or "mystorageaccount"
AZURE_STORAGE_CONTAINER = os.environ.get(
    "AZURE_STORAGE_CONTAINER") or "content"
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE") or "gptkb"
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX") or "gptkbindex"
AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE") or "myopenai"
<<<<<<< HEAD
AZURE_FORMRECOGNIZER_SERVICE = os.environ.get(
    "AZURE_FORMRECOGNIZER_SERVICE") or "myformrecognizerservice"
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"
AZURE_SPEECH_SERVICE_KEY = os.environ.get(
    "AZURE_SPEECH_SERVICE_KEY") or "YourSpeechServiceKey"
AZURE_SPEECH_SERVICE_REGION = os.environ.get(
    "AZURE_SPEECH_SERVICE_REGION") or "YourSpeechServiceRegion"

=======
AZURE_OPENAI_GPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_GPT_DEPLOYMENT") or "davinci"
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHATGPT_DEPLOYMENT") or "chat"
AZURE_OPENAI_CHATGPT_MODEL = os.environ.get("AZURE_OPENAI_CHATGPT_MODEL") or "gpt-35-turbo"
AZURE_OPENAI_EMB_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMB_DEPLOYMENT") or "embedding"
>>>>>>> 62824c3fab4ba539958e5606ea9c99b6af266fad

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT") or "content"
KB_FIELDS_CATEGORY = os.environ.get("KB_FIELDS_CATEGORY") or "category"
KB_FIELDS_SOURCEPAGE = os.environ.get("KB_FIELDS_SOURCEPAGE") or "sourcepage"

# Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage (no secrets needed,
# just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys, use separate AzureKeyCredential instances with the
# keys for each service
# If you encounter a blocking error during a DefaultAzureCredntial resolution, you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)
azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential = True)

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2023-05-15"

# Comment these two lines out if using keys, set your API key in the OPENAI_API_KEY environment variable instead
openai.api_type = "azure_ad"
openai_token = azure_credential.get_token(
    "https://cognitiveservices.azure.com/.default")
openai.api_key = openai_token.token

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_credential)
blob_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
    credential=azure_credential)
blob_container = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

# Various approaches to integrate GPT and external knowledge, most applications will use a single one of these patterns
# or some derivative, here we include several for exploration purposes
ask_approaches = {
    "rtr": RetrieveThenReadApproach(search_client, AZURE_OPENAI_CHATGPT_DEPLOYMENT, AZURE_OPENAI_CHATGPT_MODEL, AZURE_OPENAI_EMB_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rrr": ReadRetrieveReadApproach(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, AZURE_OPENAI_EMB_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT),
    "rda": ReadDecomposeAsk(search_client, AZURE_OPENAI_GPT_DEPLOYMENT, AZURE_OPENAI_EMB_DEPLOYMENT, KB_FIELDS_SOURCEPAGE, KB_FIELDS_CONTENT)
}

chat_approaches = {
    "rrr": ChatReadRetrieveReadApproach(search_client, 
                                        AZURE_OPENAI_CHATGPT_DEPLOYMENT,
                                        AZURE_OPENAI_CHATGPT_MODEL, 
                                        AZURE_OPENAI_EMB_DEPLOYMENT,
                                        KB_FIELDS_SOURCEPAGE, 
                                        KB_FIELDS_CONTENT)
}

app = Flask(__name__)


@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)

# Serve content files from blob storage from within the app to keep the example self-contained.
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.


@app.route("/content/<path>")
def content_file(path):
    blob = blob_container.get_blob_client(path).download_blob()
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return blob.readall(), 200, {"Content-Type": mime_type, "Content-Disposition": f"inline; filename={path}"}


@app.route("/ask", methods=["POST"])
def ask():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = ask_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["question"],
                     request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /ask")
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    ensure_openai_token()
    approach = request.json["approach"]
    try:
        impl = chat_approaches.get(approach)
        if not impl:
            return jsonify({"error": "unknown approach"}), 400
        r = impl.run(request.json["history"],
                     request.json.get("overrides") or {})
        return jsonify(r)
    except Exception as e:
        logging.exception("Exception in /chat")
        return jsonify({"error": str(e)}), 500


@app.route("/get_documents", methods=["POST"])
def get_document_names():
    blob_data = dict()
    for blob in blob_container.list_blobs():
        full_blob_name = blob.name
        last_hyphen_index = full_blob_name.rfind("-")
        base_name = full_blob_name[:last_hyphen_index].strip()

        # If the name is already in the dictionary, only overwrite if the new date is earlier.
        if base_name in blob_data and blob_data[base_name][0] < blob.last_modified:
            continue

        blob_data[base_name] = (
            blob.last_modified, blob.etag)  # Convert to tuple

    return list(blob_data.items())  # Convert to list of tuples


@app.route("/get_search", methods=["POST"])
def get_search():
    documents = []
    results = search_client.search(search_text="")

    for result in results:
        documents.append(result)

    return jsonify(documents)


@app.route("/delete_all_documents", methods=["POST"])
def delete_all_documents():
    print(f"Removing all documents from search index")

    while True:
        r = search_client.search("*", top=1000, include_total_count=True)

        if r.get_count() == 0:
            break

        r = search_client.delete_documents(
            documents=[{"id": d["id"]} for d in r])
        print(f"\tRemoved something from index")

        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)
    return "Deleted all documents"


@app.route("/delete_document", methods=["POST"])
def delete_document():
    data = request.get_json()
    blob_name_to_delete = data.get('name')

    if not blob_name_to_delete:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    blob_list = blob_container.list_blobs()
    for blob in blob_list:
        if blob.name.startswith(blob_name_to_delete):
            try:
                # Delete blob from storage
                blob_client_del = blob_client.get_blob_client(
                    "content", blob.name)
                blob_client_del.delete_blob()
                print(f"Blob {blob.name} has been deleted.")

            except Exception as e:
                print(f"Failed to delete blob: {blob.name}. Error: {e}")

    # Create filter for search
    print(blob_name_to_delete)
    filter = f"sourcefile eq '{blob_name_to_delete}.pdf'"

    while True:
        print("got inside the while loop")
        # Search for documents to delete
        r = search_client.search(
            search_text="*", filter=filter, top=1000, include_total_count=True)
        results = list(r)
        print(f"Count of results: {len(results)}")
        for result in results:
            print(f"Results: {result}")
        if len(results) == 0:
            break
        r = search_client.delete_documents(
            documents=[{"id": d["id"]} for d in results])
        print(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)

    return "200"


def ensure_openai_token():
    global openai_token
    if openai_token.expires_on < int(time.time()) - 60:
        openai_token = azure_credential.get_token(
            "https://cognitiveservices.azure.com/.default")
        openai.api_key = openai_token.token


def table_to_html(table):
    table_html = "<table>"
    rows = [sorted([cell for cell in table.cells if cell.row_index == i],
                   key=lambda cell: cell.column_index) for i in range(table.row_count)]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = "th" if (
                cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
            cell_spans = ""
            if cell.column_span > 1:
                cell_spans += f" colSpan={cell.column_span}"
            if cell.row_span > 1:
                cell_spans += f" rowSpan={cell.row_span}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"
    return table_html


def split_text(filename, page_map):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ",
                    "(", ")", "[", "]", "{", "}", "\t", "\n"]
    print(f"Splitting '{filename}' into sections")

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
                end = last_word  # Fall back to at least keeping a whole word
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

        section_text = all_text[start:end]
        yield (section_text, find_page(start))

        last_table_start = section_text.rfind("<table")
        if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table")):
            # If the section ends with an unclosed table, we need to start the next section with the table.
            # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
            # If last table starts inside SECTION_OVERLAP, keep overlapping
            print(
                f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}")
            start = min(end - SECTION_OVERLAP, start + last_table_start)
        else:
            start = end - SECTION_OVERLAP

    if start + SECTION_OVERLAP < end:
        yield (all_text[start:end], find_page(start))


def get_document_text(file):
    print("in document text")
    offset = 0
    page_map = []

    file.seek(0)
    # Create a temporary file
    temp = tempfile.NamedTemporaryFile(delete=False)

    # Write the contents of the uploaded file to this temporary file
    file_content = file.read()
    print("file_content")
    print(file_content)
    temp.write(file_content)
    temp.close()

    # Ensure we're not dealing with an empty file
    if not file_content:
        raise ValueError("The uploaded file is empty.")

    print("got in document text")
    print("temp.name")
    print(temp.name)
    reader = PdfReader(temp.name)
    pages = reader.pages
    for page_num, p in enumerate(pages):
        print("reading pages")
        page_text = p.extract_text()
        print("extracting text")
        page_map.append((page_num, offset, page_text))
        print("appending")
        offset += len(page_text)
        print("offset")
    print(
        f"Extracting text from '{file.filename}' using Azure Form Recognizer")
    form_recognizer_client = DocumentAnalysisClient(
        endpoint=f"https://{AZURE_FORMRECOGNIZER_SERVICE}.cognitiveservices.azure.com/", credential=azure_credential, headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
    with open(temp.name, "rb") as f:
        poller = form_recognizer_client.begin_analyze_document(
            "prebuilt-layout", document=f)
    form_recognizer_results = poller.result()

    for page_num, page in enumerate(form_recognizer_results.pages):
        tables_on_page = [
            table for table in form_recognizer_results.tables if table.bounding_regions[0].page_number == page_num + 1]

        # mark all positions of the table spans in the page
        page_offset = page.spans[0].offset
        page_length = page.spans[0].length
        table_chars = [-1]*page_length
        for table_id, table in enumerate(tables_on_page):
            for span in table.spans:
                # replace all table spans with "table_id" in table_chars array
                for i in range(span.length):
                    idx = span.offset - page_offset + i
                    if idx >= 0 and idx < page_length:
                        table_chars[idx] = table_id

        # build page text by replacing charcters in table spans with table html
        page_text = ""
        added_tables = set()
        for idx, table_id in enumerate(table_chars):
            if table_id == -1:
                page_text += form_recognizer_results.content[page_offset + idx]
            elif not table_id in added_tables:
                page_text += table_to_html(tables_on_page[table_id])
                added_tables.add(table_id)

        page_text += " "
        page_map.append((page_num, offset, page_text))
        offset += len(page_text)

    # Remove temporary file after use
    os.remove(temp.name)

    return page_map

# Uploading Documents


def blob_name_from_file_page(filename, page=0):
    name, ext = os.path.splitext(filename)
    if ext.lower() == ".pdf":
        return f"{name}-{page}.pdf"
    else:
        return filename


def upload_blobs(file: FieldStorage):
    print("in upload blob file")

    if not blob_container.exists():
        print("created container")
        blob_container.create_container()

    # if file is PDF split into pages and upload each page as a separate blob
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(file.read()))
        print("opened reader")
        pages = reader.pages
        print("opened pages")
        print("pages length ", len(pages))
        for i in range(len(pages)):
            blob_name = blob_name_from_file_page(file.filename, i)
            print(f"\tUploading blob for page {i} -> {blob_name}")
            f = io.BytesIO()
            writer = PdfWriter()
            writer.add_page(pages[i])
            writer.write(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)
    else:
        blob_name = blob_name_from_file_page(file.filename)
        # Important to reset the file pointer back to the start of the file
        file.seek(0)
        blob_container.upload_blob(blob_name, file, overwrite=True)


def create_sections(file, page_map):
    filename = file.filename  # We retrieve the filename from the uploaded file object

    for i, (section, pagenum) in enumerate(split_text(filename, page_map)):
        yield {
            "id": re.sub("[^0-9a-zA-Z_-]", "_", f"{filename}-{i}"),
            "content": section,
            "category": "category",
            "sourcepage": blob_name_from_file_page(filename, pagenum),
            "sourcefile": filename
        }


def index_sections(file, sections):
    filename = file.filename  # We retrieve the filename from the uploaded file object

    print(
        f"Indexing sections from '{filename}' into search index")
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            print(
                f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")


@app.route("/upload_document", methods=["POST"])
def upload_document():
    if 'file' not in request.files:
        return 'No file part in the request', 400

    file = request.files['file']

    if file.filename == '':
        return 'No selected file', 400

    # detect whether the file is an audio file
    mimetype = mimetypes.guess_type(file.filename)[0]
    if mimetype and mimetype.startswith('audio'):
        print(f"Processing audio file")
        # Save the audio file temporarily
        audio_path = os.path.join(
            tempfile.gettempdir(), file.filename)
        file.save(audio_path)

        # Transcribe the audio to text
        transcript = transcribe_audio(audio_path)
        os.remove(audio_path)

        # Save transcript to PDF
        pdf_tmp_filepath = os.path.join(
            tempfile.gettempdir(), f'{os.path.splitext(file.filename)[0]}.pdf')
        generate_pdf(transcript, pdf_tmp_filepath)

        # Read PDF into BytesIO object
        with open(pdf_tmp_filepath, 'rb') as f:
            pdf_bytes = f.read()
        pdf_file = BytesIO(pdf_bytes)
        pdf_file.filename = f'{os.path.splitext(file.filename)[0]}.pdf'

        # Remove temporary PDF file
        os.remove(pdf_tmp_filepath)
        print(f"Generated PDF")
        # Upload the generated PDF
        upload_blobs(pdf_file)
        page_map = get_document_text(pdf_file)
        sections = create_sections(pdf_file, page_map)
        index_sections(pdf_file, sections)
    else:
        print(f"Uploading file")
        upload_blobs(file)
        page_map = get_document_text(file)
        sections = create_sections(file, page_map)
        index_sections(file, sections)
        # for get_document_text, create_sections, and index_sections, you might need to adjust those functions
        # or save the file temporarily if they also need to read the file content

    return 'File successfully uploaded', 200


def transcribe_audio(file_name):
    print("inside the transcribe function")

    # Setup SpeechConfig
    speech_config = SpeechConfig(
        subscription="4cee7ff91f544cd8973977a2668bf540", region="eastus")
    speech_config.speech_recognition_language = "en-US"

    # Setup AudioConfig
    audio_config = AudioConfig(filename=file_name)

    # Create a speech recognizer
    speech_recognizer = SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config)

    # Define a dict for storing status
    done_dict = {'done': False}

    # Define a list for storing recognized text
    recognized_text = []

    def stop_cb(evt):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        print('CLOSING on {}'.format(evt))
        speech_recognizer.stop_continuous_recognition()
        done_dict['done'] = True

    def recognized_cb(evt):
        """callback that appends recognized text to recognized_text list"""
        print('RECOGNIZED: {}'.format(evt))
        recognized_text.append(evt.result.text)

    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # This will start the recognition process.
    speech_recognizer.start_continuous_recognition()

    while not done_dict['done']:
        time.sleep(.5)

    # Join the recognized text into one string
    full_text = ' '.join(recognized_text)
    print("\nFull text: ", full_text)
    return full_text

    # # Start transcribing the audio file
    # result = speech_recognizer.recognize_once_async()
    # final_result = result.get()
    # print("about to get the text")
    # print(final_result.text)
    # # Return the transcribed text
    # return final_result.text


def generate_pdf(transcript, output_path):
    print("given transcript")
    print(transcript)
    print(output_path)
    c = canvas.Canvas(output_path)
    c.setFont("Helvetica", 10)
    textobject = c.beginText(40, 40)
    try:
        for line in transcript.split('\n'):
            textobject.textLine(line)
        c.drawText(textobject)
        c.showPage()
    finally:
        c.save()
    return output_path

############


if __name__ == "__main__":
    app.run()
