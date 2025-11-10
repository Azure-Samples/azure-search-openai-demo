# RAG chat: Cloud-Based data ingestion with Azure Functions

This document describes the cloud-based ingestion architecture that uses Azure Functions as custom skills for Azure AI Search indexer.

## Overview

The cloud ingestion strategy provides an alternative to the local script-based ingestion (`scripts/prepdocs.sh`). Instead of processing documents locally and uploading them to Azure AI Search, the cloud approach uses:

1. **Azure Blob Storage** as the document source
2. **Azure AI Search Indexer** as the orchestration engine
3. **Three Azure Functions** acting as chained custom skills for document processing

This architecture enables serverless, scalable, and event-driven document processing.

## Architecture

TODO: Replace with a mermaid diagram like textsplitter has,
OR use my images from slides.

```ascii
┌─────────────────────────────────────────────────────────────────┐
│  USER: Upload files to blob storage (content container)        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Azure AI Search Indexer                                        │
│  - Blob data source (monitors content container)               │
│  - Skillset with 4 chained skills (3 custom + 1 built-in)     │
│  - Runs on schedule or on-demand                               │
│  - Handles retries, checkpointing, state tracking              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────────┐
         │  SKILL #1: document_extractor│
         │  (Flex Consumption Function) │
         │  HTTP Trigger                │
         │  Context: /document          │
         │  Timeout: 10 minutes         │
         └─────────────┬────────────────┘
                       │
  Input:               │ Output to /document:
  • Blob URL           │ • pages[] (text + figure ids)
  • File metadata      │ • figures[] (metadata + base64 image)
                       │
   Processes:          │
   • Download blob     │
   • Document Intelligence
   • Figure cropping (PyMuPDF)
   • Table extraction
                       │
                       ▼
         ┌─────────────────────────────┐
         │  SKILL #2: figure_processor │
         │  (Flex Consumption Function)│
         │  HTTP Trigger               │
         │  Context: /document/figures/*│
         │  Timeout: 6 minutes         │
         │  Memory: 3072 MB            │
         └─────────────┬───────────────┘
                       │
  Input (per figure): │ Output to /document/figures/*:
  • Figure bytes      │ • description (enriched)
  • Figure metadata   │ • url (enriched)
  • placeholder       │ • embedding (enriched)
  • title             │
   Processes:          │
   • Upload to blob    │
   • Describe via LLM  │
   • Embed via Vision  │
                       │
                       ▼
         ┌─────────────────────────────┐
         │  SKILL #3: Shaper Skill     │
         │  (Built-in Azure AI Search) │
         │  Context: /document          │
         └─────────────┬───────────────┘
                       │
  Purpose:            │ Output to /document:
  • Consolidate data  │ • consolidated_document:
                       │   - pages[] (from skill #1)
  Shaper combines:    │   - figures[] (enriched from skill #2)
  • Original pages    │   - file_name
  • Enriched figures  │   - storageUrl
  • File metadata     │
                       │
  Why needed:         │
  Azure AI Search enrichment tree isolates contexts.
  Data enriched at /document/figures/* doesn't automatically
  merge into /document scope. Shaper explicitly consolidates
  all fields into a single object for downstream consumption.
                       │
                       ▼
         ┌─────────────────────────────┐
         │  SKILL #4: text_processor   │
         │  (Combines, splits, embeds) │
         │  HTTP Trigger               │
         │  Context: /document          │
         │  Timeout: 5 minutes         │
         │  Memory: 2048 MB            │
         └─────────────┬───────────────┘
                       │
  Input:              │ Output:
  • consolidated_doc  │ • Array of chunks with:
    - pages[]         │   - Content text
    - figures[]       │   - Text embeddings
    - file_name       │   - Figure references + embeddings
    - storageUrl      │   - Metadata (sourcepage, etc.)
   Processes:          │
   • Enrich placeholders│
   • Split text        │
   • Generate embeddings│
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  Azure AI Search Index                                          │
│  Indexer writes enriched documents with embeddings             │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Document Extractor Function

**Location:** `app/functions/document_extractor/`

**Purpose:** First stage of processing—extracts structured content and raw figure payloads.

**Responsibilities:**

- Downloads documents from blob storage.
- Parses documents using Azure Document Intelligence or local fallbacks.
- Extracts tables as HTML fragments.
- Crops figure images with PyMuPDF and serialises them as base64 payloads.
- Emits markdown text containing `<figure id="...">` placeholders and companion metadata arrays.
- Captures per-page metadata linking text passages to figure identifiers.

**Configuration:**

- 10-minute timeout (supports large documents and multimodal preprocessing).
- 4096 MB instance memory (for document parsing and image manipulation).
- Python 3.11 runtime.
- Uses managed identity for authentication.

**Input Format (Azure Search custom skill):**

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "blobUrl": "https://storage.../content/doc.pdf",
        "fileName": "doc.pdf",
        "contentType": "application/pdf"
      }
    }
  ]
}
```

**Output Format:**

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "pages": [
          {
            "pageNumber": 0,
            "text": "Page text with <figure id=\"fig1\"></figure>",
            "figureIds": ["fig1"]
          }
        ],

        "figures": [
          {
            "id": "fig1",
            "page": 2,
            "fileName": "doc.pdf",
            "mimeType": "image/png",
            "imageBase64": "iVBORw0...",
            "bbox": [12.4, 30.1, 180.6, 210.2]
          }
        ],
        "images": []
      },
      "errors": [],
      "warnings": []
    }
  ]
}
```

### 2. Figure Processor Function

**Location:** `app/functions/figure_processor/`

**Purpose:** Second stage—turns individual figure payloads into reusable assets and embeddings.

**Responsibilities:**

- Uploads figure bytes to blob storage and generates signed URLs or stored paths.
- Produces natural-language captions via GPT-4o or Content Understanding.
- Generates image embeddings via Azure AI Vision (when multimodal is enabled).
- Emits enriched figure metadata for downstream text processing.

**Configuration:**

- 6-minute timeout (covers caption plus embedding latency for complex figures).
- 3072 MB instance memory (accommodates concurrent figure batches).
- Python 3.11 runtime.
- Uses managed identity for authentication.

**Input Format (context `/document/figures/*`):** Azure AI Search expands the skill context, calling the function once per figure and supplying a unique `recordId` for each entry in the `values` array.

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "id": "fig1",
        "fileName": "doc.pdf",
        "mimeType": "image/png",
        "imageBase64": "iVBORw0...",
        "page": 2,
        "bbox": [12.4, 30.1, 180.6, 210.2]
      }
    }
  ]
}
```

**Output Format:**

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "url": "https://storage.../images/doc-fig1.png",
        "description": "<figure><figcaption>Bar chart showing quarterly revenue</figcaption></figure>",
        "imageEmbedding": [0.789, -0.012, ...]
      },
      "errors": [],
      "warnings": []
    }
  ]
}
```

### 4. Shaper Skill (Built-in)

**Type:** Built-in Azure AI Search skill

**Purpose:** Consolidates enrichments from different contexts into a single object.

**Why Needed:**

Azure AI Search's enrichment tree isolates data by context. When the `figure_processor` skill runs at context `/document/figures/*`, it enriches individual figure objects (adding `description`, `url`, `embedding`). However, these enrichments remain isolated in the `/document/figures/*` context and don't automatically merge into the `/document` context where the `text_processor` skill operates.

The Shaper skill explicitly consolidates:

- Original `pages` array from `document_extractor`
- Enriched `figures` array with `description`, `url`, `embedding` from `figure_processor`
- File metadata (`file_name`, `storageUrl`)

This consolidated object is then passed to the `text_processor` skill, ensuring it receives all enriched data in a single, well-structured input.

**Configuration:**

- Context: `/document`
- Uses nested `inputs` syntax with `source_context` for array consolidation
- Output: `consolidated_document` object containing all required fields

**Input Mapping:**

```python
ShaperSkill(
    name="document-shaper-skill",
    context="/document",
    inputs=[
        InputFieldMappingEntry(name="pages", source="/document/pages"),
        InputFieldMappingEntry(
            name="figures",
            source_context="/document/figures/*",
            inputs=[
                InputFieldMappingEntry(name="figure_id", source="/document/figures/*/figure_id"),
                InputFieldMappingEntry(name="filename", source="/document/figures/*/filename"),
                # ... other figure fields
                InputFieldMappingEntry(name="description", source="/document/figures/*/description"),
                InputFieldMappingEntry(name="url", source="/document/figures/*/url"),
                InputFieldMappingEntry(name="embedding", source="/document/figures/*/embedding"),
            ]
        ),
        InputFieldMappingEntry(name="file_name", source="/document/metadata_storage_name"),
        InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
    ],
    outputs=[
        OutputFieldMappingEntry(name="output", target_name="consolidated_document")
    ]
)
```

**Output Format:**

The Shaper skill produces a `consolidated_document` object at `/document/consolidated_document`:

```json
{
  "consolidated_document": {
    "pages": [
      {"page_num": 0, "text": "...", "figure_ids": ["1.1"]}
    ],
    "figures": [
      {
        "figure_id": "1.1",
        "filename": "figure1_1.png",
        "description": "The image shows a logo...",
        "url": "https://storage.../images/doc/figure1_1.png",
        "embedding": [0.123, -0.456, ...]
      }
    ],
    "file_name": "document.pdf",
    "storageUrl": "https://storage.../content/document.pdf"
  }
}
```

### 5. Text Processor Function

**Location:** `app/functions/text_processor/`

**Purpose:** Third stage—recombines enriched figure metadata with text, then produces search-ready chunks.

**Responsibilities:**

- Merges processed figure metadata back into markdown placeholders.
- Preserves `<figure>` positioning so figures stay with their surrounding narrative.
- Splits text into semantically meaningful chunks using `SentenceTextSplitter`.
- Generates text embeddings via Azure OpenAI.
- Emits chunk documents referencing figure descriptors and optional image embeddings.

**Configuration:**

- 5-minute timeout (sized for batching text embeddings).
- 2048 MB instance memory (increase if batching large embeddings).
- Python 3.11 runtime.
- Uses managed identity for authentication.

Because the enrichment tree preserves the updated `/document/figures` collection after skill #2 runs, this skill receives a fully enriched array of figure descriptors alongside the markdown source.

**Input Format:**

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "text": "# Document... <figure id=\"fig1\"></figure>",
        "tables": [...],
        "figures": [
          {
            "id": "fig1",
            "url": "https://storage.../images/doc-fig1.png",
            "caption": "Bar chart...",
            "imageEmbedding": [0.789, -0.012, ...]
          }
        ],
        "fileName": "doc.pdf"
      }
    }
  ]
}
```

**Output Format:**

```json
{
  "values": [
    {
      "recordId": "1",
      "data": {
        "chunks": [
          {
            "id": "doc.pdf-0001",
            "content": "Content chunk with <figure id=\"fig1\"></figure>",
            "embedding": [0.123, -0.456, ...],
            "sourcepage": "doc.pdf-1",
            "sourcefile": "doc.pdf",
            "images": [
              {
                "id": "fig1",
                "url": "https://storage.../images/doc-fig1.png",
                "caption": "Bar chart...",
                "imageEmbedding": [0.789, -0.012, ...]
              }
            ]
          }
        ]
      },
      "errors": [],
      "warnings": []
    }
  ]
}

**Record IDs:** The indexer maintains the original document `recordId` throughout the pipeline. Skills operating on collections (such as `/document/figures/*`) emit per-item suffixes internally, but every response still maps back to the same root document when the enrichment tree is reassembled.
```

### 4. Azure AI Search Indexer

The indexer orchestrates the entire pipeline:

**Data Source:**

- Type: `azureblob`
- Container: `content`
- Monitors for new/modified blobs
- Can be configured to track deletions or soft delete markers

**Skillset:**

- Custom skill #1 (`/document` context): `document_extractor` (emits per-page text and figure payloads).
- Custom skill #2 (`/document/figures/*` context): `figure_processor` (fans out automatically so each figure is enriched independently before being merged back into `/document/figures`).
- Custom skill #3 (`/document` context): `text_processor` (combines markdown with enriched figures, then produces chunks/embeddings).
- Skill #3 consumes the per-page text output from skill #1 and the enriched figures output from skill #2.

**Indexer:**

- Runs on schedule (e.g., every 5 minutes) or on-demand
- Batch size: Configurable (e.g., 10 documents per batch)
- Handles retries with exponential backoff
- Tracks processing state per document
- Supports incremental updates (only processes changed documents)

## Shared Code: prepdocslib

All three functions share the same processing logic used by the local ingestion script.

**Location:** `app/backend/prepdocslib/`

**Shared Modules:**

- `pdfparser.py` - Document Intelligence and local PDF parsing
- `htmlparser.py` - HTML parsing
- `textparser.py` - Plain text parsing
- `textsplitter.py` - `SentenceTextSplitter` for semantic chunking
- `embeddings.py` - Azure OpenAI and image embedding services
- `blobmanager.py` - Blob storage operations
- `mediadescriber.py` - Figure description using GPT-4o or Content Understanding

**Deployment:**

Each function includes `../../backend/prepdocslib` in `requirements.txt` as a local dependency. During deployment:

1. `pip` resolves the local path dependency.
2. The function deployment packages `prepdocslib` with all its dependencies.
3. The complete package is uploaded to the function's deployment blob container.

## Configuration

### Environment Variables (Function Apps)

Both functions receive the same configuration as the backend app:

**Azure Services:**

```bash
# Storage
AZURE_STORAGE_ACCOUNT=<name>
AZURE_STORAGE_CONTAINER=content
AZURE_IMAGESTORAGE_CONTAINER=images

# Azure OpenAI
AZURE_OPENAI_SERVICE=<name>
AZURE_OPENAI_EMB_DEPLOYMENT=<deployment>
AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-3-large
AZURE_OPENAI_EMB_DIMENSIONS=3072
AZURE_OPENAI_API_VERSION=2024-06-01

# Document Intelligence
AZURE_DOCUMENTINTELLIGENCE_SERVICE=<name>

# Azure AI Vision (for multimodal)
AZURE_VISION_ENDPOINT=<url>

# Azure AI Search
AZURE_SEARCH_SERVICE=<name>
AZURE_SEARCH_INDEX=gptkbindex
```

**Custom Skill Endpoints:**

```bash
DOCUMENT_EXTRACTOR_SKILL_ENDPOINT=https://...
DOCUMENT_EXTRACTOR_SKILL_RESOURCE_ID=api://...
FIGURE_PROCESSOR_SKILL_ENDPOINT=https://...
FIGURE_PROCESSOR_SKILL_RESOURCE_ID=api://...
TEXT_PROCESSOR_SKILL_ENDPOINT=https://...
TEXT_PROCESSOR_SKILL_RESOURCE_ID=api://...
```

**Feature Flags:**

```bash
USE_VECTORS=true
USE_MULTIMODAL=false
USE_LOCAL_PDF_PARSER=false
USE_LOCAL_HTML_PARSER=false
USE_MEDIA_DESCRIBER_AZURE_CU=false
```

**Authentication:**
All functions use **managed identity** (no connection strings or keys).

### Bicep Parameters

**infra/main.parameters.json:**

```json
{
  "useCloudIngestion": {
    "value": "${USE_CLOUD_INGESTION=false}"
  }
}
```

When `useCloudIngestion=true`:

- Deploys three Azure Functions (document_extractor, figure_processor, text_processor) on the Flex Consumption plan.
- Creates managed identities with appropriate role assignments (Storage, Search, Document Intelligence, OpenAI, Vision).
- Provisions the indexer, skillset, and data source.
- Configures the backend to use cloud ingestion.

## Local vs Cloud Ingestion

### Local Ingestion (Default)

**Command:** `./scripts/prepdocs.sh`

**Process:**

1. Run `prepdocs.py` locally.
2. Upload documents to blob storage.
3. Process documents locally (parse, split, embed).
4. Upload chunks directly to Azure AI Search index.
5. MD5 tracking to skip unchanged files.

**Use Cases:**

- Initial data seeding.
- Development and testing.
- CI/CD pipelines.
- Small datasets.
- When you need immediate control.

**Pros:**

- Simple, direct control.
- Fast for small datasets.
- Works offline (can process locally before uploading).

**Cons:**

- Not scalable for large datasets.
- Requires local compute resources.
- No automatic incremental updates.

### Cloud Ingestion

**Command:** `./scripts/prepdocs.sh --use-cloud-ingestion`

**Process:**

1. Upload documents to blob storage only.
2. Indexer automatically detects new/changed documents.
3. Functions process documents in parallel (figures and text scale independently).
4. Chunks written directly to search index.
5. Indexer tracks state (no MD5 needed).

**Use Cases:**

- Production environments.
- Large datasets.
- Continuous ingestion (monitoring blob container).
- Event-driven processing.
- Horizontal scaling requirements.

**Pros:**

- Serverless, scales automatically (up to 1000 instances).
- No local compute needed.
- Built-in retry and error handling.
- Incremental updates (only processes changes).
- Cost-effective (pay only when processing).

**Cons:**

- Slightly more complex setup.
- Depends on Azure services being available.
- Indexer scheduling introduces latency (configurable).

## MD5 Tracking

**Local ingestion** uses MD5 files to track uploaded documents:

- MD5 hash stored in `data/*.md5` files.
- Used to skip re-uploading unchanged files to blob storage.
- Still needed even with cloud ingestion for initial uploads.

**Cloud ingestion** does not need MD5 for processing:

- Indexer uses blob `lastModified` timestamp.
- Automatically detects new and changed documents.
- No MD5 files created for processed chunks.

## Deployment

### Prerequisites

1. Azure CLI with Functions extension:

  ```bash
   az extension add --name functions
   ```

1. Azure Functions Core Tools v4:

  ```bash
   brew install azure-functions-core-tools@4  # macOS
   ```

### Deploy Infrastructure

```bash
azd provision
```

This creates:

- Function App (Flex Consumption plan).
- Three function deployments (`document_extractor`, `figure_processor`, `text_processor`).
- Managed identities.
- Role assignments (Storage, OpenAI, Document Intelligence, Vision, Search).
- Indexer, skillset, and data source (if `USE_CLOUD_INGESTION=true`).

### Deploy Function Code

Functions are deployed as part of `azd up` / `azd deploy`. Manual `func azure functionapp publish` steps are not supported in this workflow—always let azd handle packaging, app settings, and managed identity assignments so that the skillset stays in sync with infrastructure as code.

### Upload Initial Data

```bash
# Upload documents (triggers indexer if cloud ingestion enabled)
./scripts/prepdocs.sh

# Or explicitly use cloud ingestion
./scripts/prepdocs.sh --use-cloud-ingestion
```

## Monitoring

### Application Insights

All three functions send telemetry to Application Insights:

- Request duration and success rate.
- Custom skill execution metrics.
- Error logs with stack traces.
- Performance counters.

**View in Azure Portal:**

1. Navigate to Function App → Application Insights.
2. Check "Live Metrics" for real-time monitoring.
3. Use "Failures" blade for error analysis.

### Indexer Status

Check indexer execution history:

```bash
# Azure CLI
az search indexer show \
  --service-name <search-service> \
  --name <indexer-name>

# Or via Azure Portal
# Navigate to Search Service → Indexers → View execution history
```

### Function Logs

Stream function logs in real-time:

```bash
func azure functionapp logstream <function-app-name>
```

## Troubleshooting

### Function Timeouts

**Symptom:** Functions timing out on large documents

**Solution:**

- Increase `functionTimeout` in `host.json` (max 10 minutes for `document_extractor`).
- Increase instance memory (2048 MB or 4096 MB).
- Consider splitting very large documents before upload.

### Embedding Rate Limits

**Symptom:** HTTP 429 errors from OpenAI

**Solution:**

- The embedding service includes retry logic with exponential backoff.
- Reduce indexer batch size to process fewer documents concurrently.
- Increase OpenAI deployment capacity (TPM).

### Missing Images

**Symptom:** Figures not appearing in search results

**Solution:**

- Verify `USE_MULTIMODAL=true` is set.
- Check that images container has proper CORS settings.
- Verify function has "Storage Blob Data Contributor" role.
- Check Application Insights for image upload errors.

### Indexer Failures

**Symptom:** Indexer shows failed executions

**Solution:**

- Check indexer execution history for error details.
- Verify custom skill URLs are accessible (not 404).
- Check function authentication (managed identity or keys configured in skillset).
- Review function logs in Application Insights.

## Cost Optimization

### Function App

**Flex Consumption Billing:**

- Execution time × memory provisioned (GB-seconds).
- Number of executions.
- Always-ready instances (if configured).

**Tips:**

- Use 2048 MB memory unless you need more (text processing or multimodal workloads).
- Set appropriate timeouts (don't over-provision).
- Don't use always-ready instances for this workload (batch processing).

### Indexer

**Indexer Runs:**

- Free tier: Limited indexer runs per day.
- Standard tier: Unlimited runs.

**Tips:**

- Adjust schedule based on upload frequency (don't run too frequently).
- Use on-demand indexer runs for manual uploads.
- Enable "high water mark" change detection (only processes new/changed docs).

## Security

### Managed Identities

All authentication uses **managed identities** (no secrets):

- Function App → Storage (read content, write images).
- Function App → OpenAI (embeddings, GPT-4o).
- Function App → Document Intelligence (parsing).
- Function App → Vision (figure analysis and captioning).
- Function App → Search (index writing).

### Network Security

Optional private networking:

- Functions can be deployed in a Virtual Network.
- Private endpoints for Storage, OpenAI, Document Intelligence, Vision.
- Network isolation for production workloads.

### Access Control

Custom skills authenticate with **Microsoft Entra ID** using managed identities:

- Azure AI Search calls each function using its system- or user-assigned managed identity and the skill's `authResourceId`.
- Each Function App enables App Service Authentication (Easy Auth) and trusts tokens issued for the registered application ID.
- Disable or avoid distributing function keys; they are unnecessary when managed identity is configured.

## Performance

### Throughput

**Expected performance:**

- Document extraction: 1-2 minutes per document (with multimodal).
- Figure processing: 10-20 seconds per document (depends on vision workload).
- Text processing and embedding: 10-30 seconds per document.
- End-to-end: 2-3 minutes per document.

**Scaling:**

- Indexer batch size: 10 documents (configurable).
- Function instances: Auto-scale based on load.
- Max concurrent executions: Limited by OpenAI TPM quota.

### Optimization Tips

1. **Batch uploads:** Upload multiple documents at once for parallel processing
2. **Pre-process documents:** Remove unnecessary content before upload
3. **Tune chunk size:** Balance between retrieval quality and processing time
4. **Use local parsers:** Faster but lower quality for simple documents

## Migration from Local to Cloud Ingestion

### Step-by-Step

1. **Deploy infrastructure:**

  ```bash
   azd env set USE_CLOUD_INGESTION true
   azd provision
   ```

1. **Test with sample documents:**

  ```bash
   # Upload a few test documents
   az storage blob upload-batch \
     -s ./data -d content \
     --account-name <storage-account>
   ```

1. **Verify indexer runs:**
   - Check Azure Portal → Search Service → Indexers
   - Verify documents appear in index

1. **Upload full dataset:**

  ```bash
   ./scripts/prepdocs.sh --use-cloud-ingestion
   ```

1. **Monitor progress:**
   - Application Insights → Live Metrics
   - Indexer execution history

### Rollback

To revert to local ingestion:

```bash
azd env set USE_CLOUD_INGESTION false
./scripts/prepdocs.sh  # Uses local processing
```

## References

- [Azure AI Search Custom Skills](https://learn.microsoft.com/azure/search/cognitive-search-custom-skill-web-api)
- [Azure Functions Flex Consumption Plan](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan)
- [Azure AI Search Indexers](https://learn.microsoft.com/azure/search/search-indexer-overview)
- [Custom Skill Interface](https://learn.microsoft.com/azure/search/cognitive-search-custom-skill-interface)
