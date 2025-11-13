# Corpus Document Retrieval and Citation Testing

This guide explains how to test if your RAG system correctly retrieves information from your corpus documents and provides accurate citations.

## Quick Start

Run the corpus accuracy test:

```bash
cd tests
python test_corpus_accuracy.py
```

## What the Test Does

1. **Discovers Indexed Documents**: First, it queries the system to find what documents are in your knowledge base.

2. **Tests Corpus Retrieval**: Runs test queries and verifies:
   - Information is retrieved from your corpus documents
   - Citations point to the correct documents
   - Corpus sources are prioritized over web sources
   - Answers include proper citations

3. **Provides Detailed Analysis**: Shows:
   - Which documents were retrieved
   - What citations were generated
   - Whether expected documents were found
   - If answers properly cite sources

## Customizing Tests

Edit `test_corpus_accuracy.py` and add your own test queries in the `test_queries` list:

```python
test_queries = [
    {
        "query": "What is the code review process?",
        "expected_docs": ["Code_Review_Checklist.pdf"],
        "description": "Test retrieval from Code Review Checklist"
    },
    {
        "query": "What are the release validation steps?",
        "expected_docs": ["Release_Validation_Process.pdf"],
        "description": "Test retrieval from Release Validation Process"
    },
    # Add more queries based on your documents...
]
```

### Test Query Format

- **query**: The question to ask (should match content in your documents)
- **expected_docs**: List of document names that should be cited (e.g., `["Document1.pdf"]`)
- **description**: Brief description of what this test verifies

## Understanding Test Results

### ✅ PASS Indicators

- `[PASS] Answer includes corpus citations` - Answer properly cites corpus documents
- `[PASS] All expected documents found` - Expected documents were retrieved and cited
- `Tests with corpus sources: X/X` - All tests retrieved corpus sources

### ⚠️ WARN Indicators

- `[WARN] Answer may not be citing corpus sources properly` - Citations found but may not be in answer format
- `[WARN] Answer says 'I don't know' but corpus sources were found` - Sources retrieved but don't contain answer

### ❌ FAIL Indicators

- `[WARNING] No corpus sources found!` - Documents not retrieved (may not be indexed or query doesn't match)
- `[MISSING] Not found: [...]` - Expected documents were not retrieved

## Testing Different Scenarios

### Test 1: Corpus-Only Mode (Default)

Tests that corpus documents are retrieved correctly:

```python
result = await test_corpus_query(
    "What is the code review process?",
    expected_documents=["Code_Review_Checklist.pdf"],
    use_corpus_only=True  # Forces RAG-only, no web search
)
```

### Test 2: Hybrid Mode

Tests that corpus is prioritized over web:

```python
result = await test_corpus_query(
    "What is RAG?",
    expected_documents=None,
    use_corpus_only=False  # Allows web search as fallback
)
```

## Verifying Citation Accuracy

The test checks:

1. **Citation Format**: Citations should be in format `[DocumentName.pdf#page=N]`
2. **Citation Presence**: Citations should appear in the answer text
3. **Document Matching**: Expected documents should be in the citations list
4. **Source Priority**: Corpus sources should be used before web sources

## Troubleshooting

### No Corpus Sources Found

**Possible causes:**
- Documents not indexed in Azure AI Search
- Query doesn't match document content
- Search index needs to be rebuilt

**Solutions:**
1. Verify documents are in Azure Blob Storage
2. Run `prepdocs.py` to re-index documents
3. Check Azure AI Search index contains your documents
4. Try queries that match exact phrases from your documents

### Citations Not in Answer

**Possible causes:**
- LLM not following citation format
- Prompt not instructing citations properly

**Solutions:**
1. Check prompt templates in `app/backend/approaches/prompts/`
2. Verify citations are in the `citations` array
3. Review answer format - citations should be like `[doc.pdf#page=1]`

### Wrong Documents Cited

**Possible causes:**
- Search retrieval returning irrelevant chunks
- Similar content in multiple documents

**Solutions:**
1. Review retrieved sources in test output
2. Check if search is using correct embeddings
3. Verify document content matches query intent
4. Adjust `top` parameter to get more/fewer results

## Example Test Output

```
[TEST 1/2] Test retrieval from Code Review Checklist
================================================================================
TESTING CORPUS QUERY: What is the code review process?
================================================================================

[INFO] Query: What is the code review process?
[INFO] Mode: RAG-only (corpus)

[RESPONSE]
Answer: The code review process involves... [Code_Review_Checklist.pdf#page=1]
Answer length: 245 characters

[SOURCES ANALYSIS]
Total text sources: 2
Corpus sources: 2
Web sources: 0

[CORPUS SOURCES]
  1. Code_Review_Checklist.pdf#page=1
     Preview: Code Review Checklist This checklist serves as a guide...

[CITATIONS]
Total citations: 2
Corpus citations (2):
  1. Code_Review_Checklist.pdf#page=1
  2. Release_Validation_Process.pdf#page=1

[VERIFICATION]
Expected documents: ['Code_Review_Checklist.pdf']
[PASS] All expected documents found: ['Code_Review_Checklist.pdf']

[ACCURACY CHECK]
[PASS] Answer includes corpus citations
```

## Next Steps

1. **Add Your Test Queries**: Edit `test_corpus_accuracy.py` with queries based on your documents
2. **Run Tests**: Execute the script to verify corpus retrieval
3. **Review Results**: Check if expected documents are cited correctly
4. **Fix Issues**: Address any warnings or failures
5. **Iterate**: Add more tests as you add documents

