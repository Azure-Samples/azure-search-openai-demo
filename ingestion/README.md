# Ingestion Module

A **fully standalone**, reusable Python module for ingesting documents into Azure AI Search.

## Overview

This module is a **completely self-contained** document ingestion library that can be copied to any project without dependencies on the parent repository. It includes all parsers, splitters, embeddings, storage managers, and ingestion strategies needed for a complete document ingestion pipeline.

**Key Features:**

- Zero dependencies on external application code
- Can be moved to a different project as-is
- Includes its own `requirements.txt` for easy dependency installation
- Supports multiple document formats (PDF, HTML, text, CSV, JSON)
- Multiple ingestion strategies for different use cases

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Authentication](#authentication)
4. [Configuration](#configuration)
5. [Quick Start](#quick-start)
6. [Module Structure](#module-structure)
7. [Strategies](#strategies)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before using this module, you need to provision the following Azure resources:

### Required Azure Resources

| Resource | Purpose | How to Create |
|----------|---------|---------------|
| **Azure AI Search** | Index and search documents | [Create Search Service](https://learn.microsoft.com/azure/search/search-create-service-portal) |
| **Azure Storage Account** | Store documents and images | [Create Storage Account](https://learn.microsoft.com/azure/storage/common/storage-account-create) |
| **Azure OpenAI** | Generate text embeddings | [Create Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource) |

### Optional Azure Resources

| Resource | Purpose | When Needed |
|----------|---------|-------------|
| **Azure Document Intelligence** | Parse PDFs with high accuracy | When `use_local_pdf_parser=False` |
| **Azure AI Vision** | Generate image embeddings | When `use_multimodal=True` |
| **Azure Content Understanding** | Generate image descriptions | When using Content Understanding strategy |

### Azure OpenAI Deployments

You'll need to deploy the following models in your Azure OpenAI resource:

| Model | Recommended Deployment Name | Purpose |
|-------|----------------------------|---------|
| `text-embedding-ada-002` or `text-embedding-3-small` | `text-embedding` | Text embeddings |
| `gpt-4o` or `gpt-4` | `gpt-4o` | Image descriptions (optional) |

### Software Requirements

- **Python 3.10+**
- **Azure CLI** (for authentication)

---

## Installation

### 1. Copy the Module

Copy the entire `ingestion/` folder to your project:

```bash
cp -r ingestion/ /path/to/your/project/
```

### 2. Install Dependencies

```bash
cd /path/to/your/project/ingestion
pip install -r requirements.txt
```

Or install in your project's virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r ingestion/requirements.txt
```

### 3. Verify Installation

```python
from ingestion import IngestionConfig, upload_and_index
print("Ingestion module loaded successfully!")
```

---

## Authentication

The module uses Azure Identity for authentication. You have several options:

### Option 1: Azure Developer CLI (Recommended for Development)

```bash
# Install Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# Login
azd auth login

# Set your tenant (if needed)
azd auth login --tenant-id <your-tenant-id>
```

### Option 2: Azure CLI

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription <subscription-id>
```

### Option 3: Service Principal (Recommended for Production)

Set these environment variables:

```bash
export AZURE_CLIENT_ID="<your-client-id>"
export AZURE_CLIENT_SECRET="<your-client-secret>"
export AZURE_TENANT_ID="<your-tenant-id>"
```

### Required RBAC Permissions

Ensure your identity has these roles on the respective resources:

| Resource | Required Role |
|----------|---------------|
| Azure AI Search | `Search Index Data Contributor` |
| Azure Storage | `Storage Blob Data Contributor` |
| Azure OpenAI | `Cognitive Services OpenAI User` |
| Azure Document Intelligence | `Cognitive Services User` |
| Azure AI Vision | `Cognitive Services User` |

---

## Quick Start

### Basic Usage

```python
from ingestion import IngestionConfig, upload_and_index

# Load configuration from environment variables
config = IngestionConfig.from_env()

# Ingest documents
result = await upload_and_index(files="data/*", config=config)

if result["success"]:
    print(f"Ingestion completed using {result['strategy']}")
else:
    print(f"Errors: {result['errors']}")
```

### Using Strategies Directly

```python
from ingestion import (
    IngestionConfig,
    FileStrategy,
    SearchInfo,
    BlobManager,
    OpenAIEmbeddings,
)
from ingestion.storage import LocalListFileStrategy

# Set up components
config = IngestionConfig.from_env()
credential = AzureDeveloperCliCredential()

search_info = SearchInfo(
    endpoint=f"https://{config.search_service}.search.windows.net/",
    credential=credential,
    index_name=config.search_index,
)

blob_manager = BlobManager(
    endpoint=f"https://{config.storage_account}.blob.core.windows.net",
    container=config.storage_container,
    credential=credential,
)

list_file_strategy = LocalListFileStrategy(path_pattern="data/*")

# Create and run strategy
strategy = FileStrategy(
    list_file_strategy=list_file_strategy,
    blob_manager=blob_manager,
    search_info=search_info,
    file_processors=file_processors,
    embeddings=embeddings_service,
)

await strategy.setup()
await strategy.run()
```

## Module Structure

```
ingestion/
├── __init__.py              # Public API exports
├── config.py                # IngestionConfig dataclass, env-based configuration
├── models.py                # Data classes (File, Page, Chunk, Section, ImageOnPage)
├── utils.py                 # Shared helpers
├── uploader.py              # High-level orchestrator: upload_and_index()
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── parsers/                 # Document parsers
│   ├── __init__.py
│   ├── base.py              # Parser ABC
│   ├── pdf.py               # LocalPdfParser, DocumentAnalysisParser
│   ├── html.py              # LocalHTMLParser (BeautifulSoup)
│   ├── text.py              # TextParser (plain text, markdown)
│   ├── csv.py               # CsvParser
│   ├── json.py              # JsonParser
│   └── processor.py         # FileProcessor (parser + splitter combo)
│
├── splitters/               # Text chunking
│   ├── __init__.py
│   ├── base.py              # TextSplitter ABC
│   ├── sentence.py          # SentenceTextSplitter (semantic chunking)
│   └── simple.py            # SimpleTextSplitter (fixed-size chunks)
│
├── figures/                 # Image/figure processing
│   ├── __init__.py
│   ├── describers.py        # MediaDescriber, ContentUnderstandingDescriber
│   └── processor.py         # FigureProcessor, build_figure_markup
│
├── search/                  # Azure AI Search operations
│   ├── __init__.py
│   ├── client.py            # SearchInfo, client factories
│   └── index_manager.py     # SearchManager for index CRUD
│
├── storage/                 # Blob storage and file listing
│   ├── __init__.py
│   ├── blob.py              # BlobManager, AdlsBlobManager
│   └── file_lister.py       # ListFileStrategy implementations
│
├── embeddings/              # Embedding generation
│   ├── __init__.py
│   ├── text.py              # OpenAIEmbeddings
│   └── image.py             # ImageEmbeddings (Azure AI Vision)
│
└── strategies/              # Ingestion strategies
    ├── __init__.py
    ├── base.py              # Strategy ABC, DocumentAction enum
    ├── file.py              # FileStrategy, UploadUserFileStrategy, parse_file
    ├── integrated.py        # IntegratedVectorizerStrategy
    └── cloud.py             # CloudIngestionStrategy
```

## Configuration

The `IngestionConfig` class supports configuration via environment variables. Create a `.env` file or export these variables:

### Minimal Configuration (Required)

```bash
# Azure AI Search
export AZURE_SEARCH_SERVICE="your-search-service"
export AZURE_SEARCH_INDEX="your-index-name"

# Azure Storage
export AZURE_STORAGE_ACCOUNT="yourstorageaccount"
export AZURE_STORAGE_CONTAINER="documents"

# Azure OpenAI
export AZURE_OPENAI_SERVICE="your-openai-service"
export AZURE_OPENAI_EMB_DEPLOYMENT="text-embedding"
export AZURE_OPENAI_EMB_MODEL_NAME="text-embedding-ada-002"

# Authentication
export AZURE_TENANT_ID="your-tenant-id"
```

### Complete Environment Variables Reference

#### Core Azure Services

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_SEARCH_SERVICE` | ✅ | - | Azure AI Search service name |
| `AZURE_SEARCH_INDEX` | ✅ | - | Search index name |
| `AZURE_STORAGE_ACCOUNT` | ✅ | - | Azure Storage account name |
| `AZURE_STORAGE_CONTAINER` | ✅ | - | Blob container for documents |
| `AZURE_TENANT_ID` | ✅ | - | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | ❌ | - | Azure subscription ID |

#### OpenAI Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_HOST` | ❌ | `azure` | Hosting: `azure`, `openai`, or `local` |
| `AZURE_OPENAI_SERVICE` | ✅* | - | Azure OpenAI service name |
| `AZURE_OPENAI_EMB_DEPLOYMENT` | ✅* | - | Embedding model deployment name |
| `AZURE_OPENAI_EMB_MODEL_NAME` | ❌ | `text-embedding-ada-002` | Embedding model name |
| `AZURE_OPENAI_EMB_DIMENSIONS` | ❌ | - | Embedding dimensions (for ada-002: 1536) |
| `OPENAI_API_KEY` | ✅** | - | OpenAI API key (when `OPENAI_HOST=openai`) |
| `OPENAI_ORGANIZATION` | ❌ | - | OpenAI organization ID |

*Required when `OPENAI_HOST=azure`  
**Required when `OPENAI_HOST=openai`

#### Document Intelligence (PDF Parsing)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_DOCUMENTINTELLIGENCE_SERVICE` | ❌ | - | Document Intelligence service name |
| `AZURE_DOCUMENTINTELLIGENCE_KEY` | ❌ | - | API key (optional, uses managed identity if not set) |
| `USE_LOCAL_PDF_PARSER` | ❌ | `false` | Use local pypdf instead of Document Intelligence |
| `USE_LOCAL_HTML_PARSER` | ❌ | `true` | Use local BeautifulSoup for HTML |

#### Multimodal / Image Processing

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_MULTIMODAL` | ❌ | `false` | Enable image extraction and processing |
| `AZURE_VISION_ENDPOINT` | ❌ | - | Azure AI Vision endpoint for image embeddings |
| `USE_CONTENT_UNDERSTANDING` | ❌ | `false` | Use Content Understanding for image descriptions |
| `AZURE_CONTENT_UNDERSTANDING_ENDPOINT` | ❌ | - | Content Understanding endpoint |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | ❌ | - | GPT-4 deployment for image descriptions |
| `AZURE_OPENAI_CHATGPT_MODEL` | ❌ | `gpt-4o` | GPT model for image descriptions |

#### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_VECTORS` | ❌ | `true` | Enable text embeddings |
| `USE_GPT4V` | ❌ | `false` | Enable GPT-4 Vision for image descriptions |
| `USE_FEATURE_INT_VECTORIZATION` | ❌ | `false` | Use Azure AI Search integrated vectorization |
| `USE_CLOUD_INGESTION` | ❌ | `false` | Use cloud-based ingestion with Azure Functions |

#### Advanced Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_SEARCH_ANALYZER_NAME` | ❌ | `en.microsoft` | Search analyzer for text fields |
| `AZURE_SEARCH_FIELD_NAME_EMBEDDING` | ❌ | `embedding` | Field name for embeddings |
| `AZURE_STORAGE_RESOURCE_GROUP` | ❌ | - | Storage account resource group |
| `AZURE_ADLS_GEN2_STORAGE_ACCOUNT` | ❌ | - | Data Lake Storage account |
| `AZURE_ADLS_GEN2_FILESYSTEM` | ❌ | - | Data Lake filesystem name |
| `AZURE_ADLS_GEN2_FILESYSTEM_PATH` | ❌ | - | Path within the filesystem |

### Example .env File

```bash
# .env file for ingestion module

# Required: Azure AI Search
AZURE_SEARCH_SERVICE=my-search-service
AZURE_SEARCH_INDEX=documents-index

# Required: Azure Storage
AZURE_STORAGE_ACCOUNT=mystorageaccount
AZURE_STORAGE_CONTAINER=documents

# Required: Azure OpenAI
AZURE_OPENAI_SERVICE=my-openai-service
AZURE_OPENAI_EMB_DEPLOYMENT=text-embedding
AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-ada-002

# Required: Authentication
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Optional: Document Intelligence for better PDF parsing
AZURE_DOCUMENTINTELLIGENCE_SERVICE=my-doc-intelligence

# Optional: Enable multimodal (image processing)
USE_MULTIMODAL=false
AZURE_VISION_ENDPOINT=https://my-vision.cognitiveservices.azure.com/

# Optional: Feature flags
USE_VECTORS=true
USE_LOCAL_PDF_PARSER=false
```

### Loading Configuration

```python
from ingestion import IngestionConfig

# Load from environment variables
config = IngestionConfig.from_env()

# Or create programmatically with overrides
config = IngestionConfig(
    search_service="my-search-service",
    search_index="my-index",
    storage_account="mystorageaccount",
    storage_container="documents",
    azure_openai_service="my-openai",
    azure_openai_emb_deployment="text-embedding",
    tenant_id="your-tenant-id",
)

# Validate configuration
errors = config.validate()
if errors:
    print(f"Configuration errors: {errors}")
```

---

## Strategies

### FileStrategy

Local file-based ingestion with client-side document processing:

- Parses documents locally using Document Intelligence or local parsers
- Generates embeddings using OpenAI/Azure OpenAI
- Uploads documents and sections to Azure

### IntegratedVectorizerStrategy

Uses Azure AI Search's built-in vectorization:

- Creates a skillset with split and embedding skills
- Uses an indexer to process documents from blob storage
- Ideal for large-scale ingestion with minimal client-side processing

### CloudIngestionStrategy

Cloud-based ingestion using Azure Functions:

- Uses custom Web API skills backed by Azure Functions
- Supports document extraction, figure processing, and text processing
- Best for complex document processing pipelines

---

## API Reference

### High-Level Functions

#### `upload_and_index()`

The main entry point for document ingestion:

```python
async def upload_and_index(
    files: Optional[str] = None,           # Path pattern for local files (e.g., "data/*")
    config: Optional[IngestionConfig] = None,  # Configuration (defaults to env vars)
    credential: Optional[AsyncTokenCredential] = None,  # Azure credential
    action: DocumentAction = DocumentAction.Add,  # Add, Remove, or RemoveAll
    category: Optional[str] = None,        # Category for all documents
    setup_index: bool = True,              # Create/update search index
) -> dict:
    """Returns {"success": bool, "strategy": str, "errors": list}"""
```

#### `build_file_processors()`

Create file processors for different document types:

```python
def build_file_processors(
    azure_credential: AsyncTokenCredential,
    document_intelligence_service: Optional[str] = None,
    document_intelligence_key: Optional[str] = None,
    use_local_pdf_parser: bool = False,
    use_local_html_parser: bool = False,
    process_figures: bool = False,
) -> dict[str, FileProcessor]:
    """Returns {".pdf": FileProcessor, ".html": FileProcessor, ...}"""
```

#### `parse_file()`

Parse a single file into sections:

```python
async def parse_file(
    file: File,
    file_processors: dict,
    category: Optional[str] = None,
    blob_manager: Optional[BaseBlobManager] = None,
    image_embeddings_client: Optional[ImageEmbeddings] = None,
    figure_processor: Optional[FigureProcessor] = None,
    user_oid: Optional[str] = None,
) -> list[Section]:
    """Returns list of Section objects ready for indexing"""
```

### Key Classes

| Class | Description |
|-------|-------------|
| `IngestionConfig` | Configuration dataclass with `from_env()` and `validate()` |
| `File` | Represents a file with content and metadata |
| `Page` | Represents a parsed page with text and images |
| `Chunk` | A text chunk after splitting |
| `Section` | A chunk with metadata ready for indexing |
| `ImageOnPage` | An image extracted from a document |
| `SearchInfo` | Azure AI Search connection info |
| `SearchManager` | Manages search index operations |
| `BlobManager` | Manages Azure Blob Storage operations |
| `OpenAIEmbeddings` | Generates text embeddings |
| `ImageEmbeddings` | Generates image embeddings |
| `FileStrategy` | Local file ingestion strategy |
| `IntegratedVectorizerStrategy` | Azure AI Search integrated vectorization |
| `CloudIngestionStrategy` | Cloud-based ingestion with Azure Functions |

### Parsers

| Parser | File Types | Description |
|--------|------------|-------------|
| `LocalPdfParser` | `.pdf` | Uses pypdf for local PDF parsing |
| `DocumentAnalysisParser` | `.pdf` | Uses Azure Document Intelligence |
| `LocalHTMLParser` | `.html`, `.htm` | Uses BeautifulSoup |
| `TextParser` | `.txt`, `.md` | Plain text and markdown |
| `CsvParser` | `.csv` | CSV files (one row = one page) |
| `JsonParser` | `.json` | JSON files |

### Splitters

| Splitter | Description |
|----------|-------------|
| `SentenceTextSplitter` | Semantic chunking with sentence awareness |
| `SimpleTextSplitter` | Fixed-size character-based chunking |

---

## Troubleshooting

### Common Errors

#### Authentication Errors

**Error:** `DefaultAzureCredential failed to retrieve a token`

**Solution:**

```bash
# Ensure you're logged in
azd auth login
# Or
az login

# Verify your tenant
az account show
```

#### Missing Environment Variables

**Error:** `Configuration errors: ['search_service is required']`

**Solution:** Ensure all required environment variables are set:

```bash
# Check if variables are set
echo $AZURE_SEARCH_SERVICE
echo $AZURE_STORAGE_ACCOUNT
echo $AZURE_OPENAI_SERVICE
```

#### Permission Denied

**Error:** `AuthorizationPermissionMismatch` or `403 Forbidden`

**Solution:** Ensure your identity has the correct RBAC roles:

```bash
# Assign Search Index Data Contributor
az role assignment create \
  --assignee <your-user-or-sp-id> \
  --role "Search Index Data Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search-service>

# Assign Storage Blob Data Contributor
az role assignment create \
  --assignee <your-user-or-sp-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>
```

#### Document Intelligence Errors

**Error:** `InvalidRequest` when parsing PDFs

**Solution:** Either:
1. Set up Azure Document Intelligence service
2. Or use local parser: `USE_LOCAL_PDF_PARSER=true`

#### Embedding Dimension Mismatch

**Error:** `Vector field dimension mismatch`

**Solution:** Ensure your embedding model dimensions match the index:
- `text-embedding-ada-002`: 1536 dimensions
- `text-embedding-3-small`: 1536 dimensions (default) or custom
- `text-embedding-3-large`: 3072 dimensions (default) or custom

Set `AZURE_OPENAI_EMB_DIMENSIONS` if using a non-default dimension.

### Debugging Tips

1. **Enable verbose logging:**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logging.getLogger("ingestion").setLevel(logging.DEBUG)
   ```

2. **Validate configuration before running:**

   ```python
   config = IngestionConfig.from_env()
   errors = config.validate()
   if errors:
       print(f"Config errors: {errors}")
   ```

3. **Test Azure connectivity:**

   ```python
   from azure.identity import DefaultAzureCredential
   credential = DefaultAzureCredential()
   token = credential.get_token("https://search.azure.com/.default")
   print("Authentication successful!")
   ```

4. **Check search index exists:**

   ```python
   from azure.search.documents.indexes import SearchIndexClient
   client = SearchIndexClient(endpoint, credential)
   indexes = list(client.list_indexes())
   print([idx.name for idx in indexes])
   ```

---

## Examples

### Example 1: Simple Local File Ingestion

```python
import asyncio
from ingestion import IngestionConfig, upload_and_index

async def main():
    config = IngestionConfig.from_env()
    result = await upload_and_index(files="./documents/*.pdf", config=config)
    
    if result["success"]:
        print(f"✅ Ingested using {result['strategy']}")
    else:
        print(f"❌ Errors: {result['errors']}")

asyncio.run(main())
```

### Example 2: Custom Parser Configuration

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from ingestion import (
    IngestionConfig, FileStrategy, SearchInfo, BlobManager,
    OpenAIEmbeddings, build_file_processors, parse_file
)
from ingestion.storage import LocalListFileStrategy

async def main():
    config = IngestionConfig.from_env()
    credential = DefaultAzureCredential()
    
    # Build custom file processors
    file_processors = build_file_processors(
        azure_credential=credential,
        document_intelligence_service=config.document_intelligence_service,
        use_local_pdf_parser=True,  # Use local parser
        process_figures=False,
    )
    
    # Set up components
    search_info = SearchInfo(
        endpoint=f"https://{config.search_service}.search.windows.net/",
        credential=credential,
        index_name=config.search_index,
    )
    
    blob_manager = BlobManager(
        endpoint=f"https://{config.storage_account}.blob.core.windows.net",
        container=config.storage_container,
        credential=credential,
    )
    
    list_strategy = LocalListFileStrategy(path_pattern="./data/*.pdf")
    
    # Create and run strategy
    strategy = FileStrategy(
        list_file_strategy=list_strategy,
        blob_manager=blob_manager,
        search_info=search_info,
        file_processors=file_processors,
        embeddings=None,  # No embeddings
    )
    
    await strategy.setup()
    await strategy.run()
    
    await credential.close()

asyncio.run(main())
```

### Example 3: Processing a Single File

```python
import asyncio
from azure.identity.aio import DefaultAzureCredential
from ingestion import File, build_file_processors, parse_file

async def main():
    credential = DefaultAzureCredential()
    
    file_processors = build_file_processors(
        azure_credential=credential,
        use_local_pdf_parser=True,
    )
    
    # Create a File object
    with open("document.pdf", "rb") as f:
        file = File(content=f)
        file.filename = lambda: "document.pdf"
        file.file_extension = lambda: ".pdf"
        
        sections = await parse_file(
            file=file,
            file_processors=file_processors,
        )
        
        print(f"Parsed {len(sections)} sections")
        for i, section in enumerate(sections[:3]):
            print(f"Section {i}: {section.chunk.text[:100]}...")
    
    await credential.close()

asyncio.run(main())
```

---

## License

This module is licensed under the MIT License.
