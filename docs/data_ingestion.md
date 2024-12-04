# RAG chat: Data ingestion

The [azure-search-openai-demo](/) project can set up a full RAG chat app on Azure AI Search and OpenAI so that you can chat on custom data, like internal enterprise data or domain-specific knowledge sets. For full instructions on setting up the project, consult the [main README](/README.md), and then return here for detailed instructions on the data ingestion component.

The chat app provides two ways to ingest data: manual indexing and integrated vectorization. This document explains the differences between the two approaches and provides an overview of the manual indexing process.

- [Supported document formats](#supported-document-formats)
- [Manual indexing process](#manual-indexing-process)
  - [Chunking](#chunking)
  - [Categorizing data for enhanced search](#enhancing-search-functionality-with-data-categorization)
  - [Indexing additional documents](#indexing-additional-documents)
  - [Removing documents](#removing-documents)
- [Integrated Vectorization](#integrated-vectorization)
  - [Indexing of additional documents](#indexing-of-additional-documents)
  - [Removal of documents](#removal-of-documents)
  - [Scheduled indexing](#scheduled-indexing)
- [Debugging tips](#debugging-tips)

## Supported document formats

In order to ingest a document format, we need a tool that can turn it into text. By default, the manual indexing uses Azure Document Intelligence (DI in the table below), but we also have local parsers for several formats. The local parsers are not as sophisticated as Azure Document Intelligence, but they can be used to decrease charges.

| Format | Manual indexing                      | Integrated Vectorization |
| ------ | ------------------------------------ | ------------------------ |
| PDF    | Yes (DI or local with PyPDF)         | Yes                      |
| HTML   | Yes (DI or local with BeautifulSoup) | Yes                      |
| DOCX, PPTX, XLSX   | Yes (DI)                             | Yes                      |
| Images (JPG, PNG, BPM, TIFF, HEIFF)| Yes (DI) | Yes                      |
| TXT    | Yes (Local)                          | Yes                      |
| JSON   | Yes (Local)                          | Yes                      |
| CSV    | Yes (Local)                          | Yes                      |

The Blob indexer used by the Integrated Vectorization approach also supports a few [additional formats](https://learn.microsoft.com/azure/search/search-howto-indexing-azure-blob-storage#supported-document-formats).

## Manual indexing process

The [`prepdocs.py`](../app/backend/prepdocs.py) script is responsible for both uploading and indexing documents. The typical usage is to call it using `scripts/prepdocs.sh` (Mac/Linux) or `scripts/prepdocs.ps1` (Windows), as these scripts will set up a Python virtual environment and pass in the required parameters based on the current `azd` environment. You can pass additional arguments directly to the script, for example `scripts/prepdocs.ps1 --removeall`. Whenever `azd up` or `azd provision` is run, the script is called automatically.

![Diagram of the indexing process](images/diagram_prepdocs.png)

The script uses the following steps to index documents:

1. If it doesn't yet exist, create a new index in Azure AI Search.
2. Upload the PDFs to Azure Blob Storage.
3. Split the PDFs into chunks of text.
4. Upload the chunks to Azure AI Search. If using vectors (the default), also compute the embeddings and upload those alongside the text.

### Chunking

We're often asked why we need to break up the PDFs into chunks when Azure AI Search supports searching large documents.

Chunking allows us to limit the amount of information we send to OpenAI due to token limits. By breaking up the content, it allows us to easily find potential chunks of text that we can inject into OpenAI. The method of chunking we use leverages a sliding window of text such that sentences that end one chunk will start the next. This allows us to reduce the chance of losing the context of the text.

If needed, you can modify the chunking algorithm in `app/backend/prepdocslib/textsplitter.py`.

### Enhancing search functionality with data categorization

To enhance search functionality, categorize data during the ingestion process with the `--category` argument, for example `scripts/prepdocs.ps1 --category ExampleCategoryName`. This argument specifies the category to which the data belongs, enabling you to filter search results based on these categories.

After running the script with the desired category, ensure these categories are added to the 'Include Category' dropdown list. This can be found in the developer settings in [`Settings.tsx`](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/frontend/src/components/Settings/Settings.tsx). The default option for this dropdown is "All". By including specific categories, you can refine your search results more effectively.

### Indexing additional documents

To upload more PDFs, put them in the data/ folder and run `./scripts/prepdocs.sh` or `./scripts/prepdocs.ps1`.

A [recent change](https://github.com/Azure-Samples/azure-search-openai-demo/pull/835) added checks to see what's been uploaded before. The prepdocs script now writes an .md5 file with an MD5 hash of each file that gets uploaded. Whenever the prepdocs script is re-run, that hash is checked against the current hash and the file is skipped if it hasn't changed.

### Removing documents

You may want to remove documents from the index. For example, if you're using the sample data, you may want to remove the documents that are already in the index before adding your own.

To remove all documents, use `./scripts/prepdocs.sh --removeall` or `./scripts/prepdocs.ps1 --removeall`.

You can also remove individual documents by using the `--remove` flag. Open either `scripts/prepdocs.sh` or `scripts/prepdocs.ps1` and replace `/data/*` with `/data/YOUR-DOCUMENT-FILENAME-GOES-HERE.pdf`. Then run `scripts/prepdocs.sh --remove` or `scripts/prepdocs.ps1 --remove`.

## Integrated Vectorization

Azure AI Search includes an [integrated vectorization feature](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/announcing-the-public-preview-of-integrated-vectorization-in-azure-ai-search/3960809), a cloud-based approach to data ingestion. Integrated vectorization takes care of document format cracking, data extraction, chunking, vectorization, and indexing, all with Azure technologies.

See [this notebook](https://github.com/Azure/azure-search-vector-samples/blob/main/demo-python/code/integrated-vectorization/azure-search-integrated-vectorization-sample.ipynb) to understand the process of setting up integrated vectorization.
We have integrated that code into our `prepdocs` script, so you can use it without needing to understand the details.

You must first explicitly [enable integrated vectorization](./deploy_features.md#enabling-integrated-vectorization) in the `azd` environment to use this feature.

This feature cannot be used on existing index. You need to create a new index or drop and recreate an existing index.
In the newly created index schema, a new field 'parent_id' is added. This is used internally by the indexer to manage life cycle of chunks.

This feature is not supported in the free SKU for Azure AI Search.

### Indexing of additional documents

To add additional documents to the index, first upload them to your data source (Blob storage, by default).
Then navigate to the Azure portal, find the index, and run it.
The Azure AI Search indexer will identify the new documents and ingest them into the index.

### Removal of documents

To remove documents from the index, remove them from your data source (Blob storage, by default).
Then navigate to the Azure portal, find the index, and run it.
The Azure AI Search indexer will take care of removing those documents from the index.

### Scheduled indexing

If you would like the indexer to run automatically, you can set it up to [run on a schedule](https://learn.microsoft.com/azure/search/search-howto-schedule-indexers).

## Debugging tips

If you are not sure if a file successfully uploaded, you can query the index from the Azure Portal or from the REST API. Open the index and paste the queries below into the search bar.

To see all the filenames uploaded to the index:

```json
{
  "search": "*",
  "count": true,
  "top": 1,
  "facets": ["sourcefile"]
}
```

To search for specific filenames:

```json
{
  "search": "*",
  "count": true,
  "top": 1,
  "filter": "sourcefile eq 'employee_handbook.pdf'",
  "facets": ["sourcefile"]
}
```
