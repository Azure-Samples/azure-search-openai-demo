# NOMIC Embeddings Implementation

## Overview

NOMIC embeddings have been fully implemented in the AI Master Engineer application. This implementation supports multiple NOMIC models (text, code, and vision) with intelligent routing based on content analysis.

## Implementation Summary

### 1. NOMIC Embeddings Client (`app/backend/prepdocslib/nomic_embeddings.py`)

**Features:**
- Support for multiple NOMIC models:
  - `nomic-embed-text-v1.5`: General text embeddings
  - `nomic-embed-code-v1`: Code-specific embeddings
  - `nomic-embed-vision-v1.5`: Multimodal (text + image) embeddings
- Dual access modes:
  - **API Mode**: Uses NOMIC API endpoint (default)
  - **SDK Mode**: Uses NOMIC Python SDK (optional, for local inference)
- Batch processing with configurable batch size
- Retry logic with exponential backoff
- Compatible interface with existing embedding services

**Key Methods:**
- `create_embedding(text)`: Single text embedding
- `create_embeddings(texts)`: Batch embeddings
- `get_embedding_dimensions()`: Returns 768 (standard NOMIC dimension)

### 2. Enhanced Embedding Router (`app/backend/services/embedding_router.py`)

**New Features:**
- **Code Detection**: Detects code-heavy content using:
  - File extension matching (`.py`, `.js`, `.java`, `.go`, etc.)
  - Code pattern detection (keywords, syntax patterns)
  - Structural indicators (brackets, semicolons, etc.)
- **Multimodal Detection**: Routes high image-density documents to NOMIC Vision
- **Intelligent Routing**:
  ```
  Code-heavy content (score >= 15.0 or code file) → NOMIC Embed Code
  High image density (>= 15%) → NOMIC Embed Vision
  Technical/Patent content → PatentSBERTa
  General content → Baseline (Azure OpenAI)
  ```

**Routing Logic:**
1. Check for explicit metadata routing hints
2. Detect code-heavy content → NOMIC Code
3. Detect high image density → NOMIC Vision
4. Detect patent/technical content → PatentSBERTa
5. Default → Baseline (Azure OpenAI)

### 3. Configuration (`app/backend/config.py`)

**New Environment Variables:**
```python
NOMIC_API_KEY              # NOMIC API key (required for API mode)
NOMIC_ENDPOINT            # Optional custom endpoint URL
NOMIC_USE_SDK             # Use Python SDK instead of API (default: false)
NOMIC_INFERENCE_MODE      # local or remote (SDK only, default: remote)
ENABLE_NOMIC_EMBEDDINGS   # Feature flag to enable NOMIC (default: false)
```

### 4. Document Ingestion Integration (`app/backend/prepdocs.py`)

**Changes:**
- Added `NOMIC` to `OpenAIHost` enum
- Updated `setup_embeddings_service()` to support NOMIC
- Added NOMIC parameters to embedding service setup
- Environment variable support for NOMIC configuration

### 5. Search Manager Compatibility (`app/backend/prepdocslib/searchmanager.py`)

**Changes:**
- Enhanced embedding dimension detection to support NOMIC
- Added fallback for direct `embedding_dimensions` attribute

## Usage

### 1. Basic Setup

**Using NOMIC API (Recommended):**
```bash
export NOMIC_API_KEY="your-api-key"
export OPENAI_HOST="nomic"
export NOMIC_MODEL="nomic-embed-text-v1.5"  # Optional, defaults to text
```

**Using NOMIC SDK (Local Inference):**
```bash
export NOMIC_USE_SDK="true"
export NOMIC_INFERENCE_MODE="local"
pip install nomic  # Install SDK
```

### 2. Automatic Routing (Recommended)

The embedding router automatically selects the best model:

```python
from services.embedding_router import EmbeddingRouter

router = EmbeddingRouter(
    baseline_deployment="text-embedding-3-large",
    nomic_api_key=os.getenv("NOMIC_API_KEY"),
    nomic_endpoint=os.getenv("NOMIC_ENDPOINT"),  # Optional
)

# Automatically routes based on content
model = router.select_model(
    content="def hello_world():\n    print('Hello')",
    content_type=".py",
    metadata={"image_count": 0}
)
# Returns: EmbeddingModel.NOMIC

# Get routing decision details
info = router.get_routing_decision_info(content, content_type, metadata)
# Returns detailed analysis and selected model
```

### 3. Manual Selection

**For Code Documents:**
```python
from prepdocslib.nomic_embeddings import create_nomic_code_embeddings

embeddings = create_nomic_code_embeddings(
    api_key=os.getenv("NOMIC_API_KEY")
)

result = await embeddings.create_embeddings([
    "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
])
```

**For Multimodal Content:**
```python
from prepdocslib.nomic_embeddings import create_nomic_vision_embeddings

embeddings = create_nomic_vision_embeddings(
    api_key=os.getenv("NOMIC_API_KEY")
)

result = await embeddings.create_embeddings([
    "This diagram shows the system architecture with three layers..."
])
```

### 4. Document Ingestion

**Using NOMIC for all embeddings:**
```bash
export OPENAI_HOST="nomic"
export NOMIC_API_KEY="your-api-key"
python prepdocs.py data/
```

**Using automatic routing (requires embedding router integration):**
- Set up embedding router with NOMIC credentials
- Router will automatically select NOMIC for code-heavy or multimodal content
- PatentSBERTa for technical/patent content
- Baseline for general content

## Configuration Examples

### Example 1: Code-Heavy Repository
```bash
# Router will automatically use NOMIC Code for .py, .js, etc.
export NOMIC_API_KEY="your-key"
export ENABLE_NOMIC_EMBEDDINGS="true"
# Router configured in app.py
```

### Example 2: Cost Optimization
```bash
# Use NOMIC for general content instead of Azure OpenAI
export OPENAI_HOST="nomic"
export NOMIC_API_KEY="your-key"
export NOMIC_MODEL="nomic-embed-text-v1.5"
```

### Example 3: Multimodal Documents
```bash
# Router will use NOMIC Vision for high image-density docs
export NOMIC_API_KEY="your-key"
export ENABLE_NOMIC_EMBEDDINGS="true"
# Documents with >15% image density will use NOMIC Vision
```

## File Structure

```
app/backend/
├── prepdocslib/
│   └── nomic_embeddings.py          # NOMIC embeddings client
├── services/
│   └── embedding_router.py           # Enhanced with NOMIC routing
├── config.py                         # NOMIC configuration
└── prepdocs.py                       # Document ingestion with NOMIC support
```

## Testing

### Test NOMIC Embeddings Client
```python
import asyncio
from prepdocslib.nomic_embeddings import NomicEmbeddings

async def test():
    embeddings = NomicEmbeddings(
        model="nomic-embed-text-v1.5",
        api_key="your-api-key"
    )
    result = await embeddings.create_embedding("Hello world")
    print(f"Embedding dimensions: {len(result)}")  # Should be 768

asyncio.run(test())
```

### Test Routing Logic
```python
from services.embedding_router import EmbeddingRouter

router = EmbeddingRouter(
    baseline_deployment="baseline",
    nomic_api_key="your-key"
)

# Test code detection
result = router.select_model(
    content="def hello():\n    return 'world'",
    content_type=".py"
)
assert result == EmbeddingModel.NOMIC
```

## Benefits

1. **Code Search**: NOMIC Embed Code provides superior code understanding
2. **Cost Optimization**: Open-source alternative to Azure OpenAI
3. **Multimodal Support**: Unified text+image embeddings
4. **Automatic Routing**: Intelligent model selection based on content
5. **Flexible Deployment**: API or SDK modes

## Next Steps

1. **Test with real code repositories**: Index code documentation and test retrieval
2. **Benchmark performance**: Compare NOMIC vs Azure OpenAI for different content types
3. **Monitor costs**: Track cost savings when using NOMIC for general content
4. **Fine-tune thresholds**: Adjust routing thresholds based on real-world performance

## Troubleshooting

### Issue: "NOMIC SDK not installed"
**Solution:** Install SDK or use API mode
```bash
pip install nomic  # For SDK mode
# OR
export NOMIC_USE_SDK="false"  # Use API mode (default)
```

### Issue: "NOMIC API error 401"
**Solution:** Check API key
```bash
export NOMIC_API_KEY="your-valid-api-key"
```

### Issue: Routing not working
**Solution:** Ensure NOMIC is configured in embedding router
```python
router = EmbeddingRouter(
    baseline_deployment="...",
    nomic_api_key=os.getenv("NOMIC_API_KEY")  # Required for routing
)
```

## References

- [NOMIC Embeddings Documentation](https://docs.nomic.ai/atlas/capabilities/embeddings)
- [NOMIC Python SDK](https://github.com/nomic-ai/nomic)
- [Use Cases Document](./nomic-embeddings-use-cases.md)





