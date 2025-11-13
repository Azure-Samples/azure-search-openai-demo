# Complete Functionality Testing Guide

## Overview

The `test_functionality.py` script tests the complete functionality of your application, including:
- Backend API endpoints (health, config, chat, ask)
- RAG responses with citations
- OCR functionality (if enabled)
- Web search (if enabled)
- Agents service (if running)
- Cache functionality
- Embedding router

## Prerequisites

1. **Backend service must be running:**
   ```powershell
   cd app\backend
   uvicorn main:app --reload
   ```

2. **Agents service (optional):**
   ```powershell
   cd agents
   python main.py
   ```

3. **Environment variables configured:**
   - Run `python tests/check_env_vars.py` to verify

## Running the Tests

### Basic Test (Default URLs)
```powershell
cd tests
python test_functionality.py
```

### Custom URLs
```powershell
python test_functionality.py --backend-url http://localhost:50505 --agents-url http://localhost:8000
```

## What Gets Tested

### 1. Backend Health ✅
- Tests `/health` endpoint
- Verifies service status and dependencies

### 2. Backend Config ✅
- Tests `/config` endpoint
- Checks available features

### 3. Cache Functionality ✅
- Tests Redis or in-memory cache
- Verifies set/get operations

### 4. Embedding Router ✅
- Tests model selection logic
- Verifies routing decisions

### 5. OCR Functionality ✅
- Checks if OCR is enabled
- Verifies OCR service configuration
- Tests OCR service initialization

### 6. Web Search Functionality ✅
- Checks if web search is enabled
- Verifies SERPER API key is set

### 7. Chat Endpoint ✅
- Tests `/chat` POST endpoint
- Sends a real query: "What is RAG?"
- Verifies response structure
- Checks for citations
- Validates answer quality

### 8. Ask Endpoint ✅
- Tests `/ask` POST endpoint
- Sends a real query: "Explain vector search"
- Verifies response structure
- Checks for citations

### 9. Agents Service Health ✅
- Tests agents service `/api/health` endpoint
- Verifies connectivity to backend

## Expected Results

### Success Output
```
[PASS] Backend is healthy
[PASS] Config endpoint working
[PASS] Cache working (Redis/In-memory)
[PASS] Embedding router working
[PASS] Chat endpoint working
  Answer length: 250 characters
  Citations: 3
[PASS] Ask endpoint working
```

### Failure Output
```
[FAIL] Backend not running at http://localhost:50505
[SKIP] Agents service not running
[WARN] No citations found
```

## Troubleshooting

### Backend Not Running
```powershell
# Start backend
cd app\backend
uvicorn main:app --reload
```

### Authentication Required
If endpoints return 401, you may need to:
1. Disable authentication for testing
2. Or provide auth tokens in the test script

### No Citations
- Ensure documents are indexed in Azure AI Search
- Check that search index has content
- Verify search service is accessible

### Empty Answers
- Check Azure OpenAI service is accessible
- Verify API keys are set correctly
- Check service logs for errors

## Advanced Testing

### Test with Custom Queries
Edit `test_functionality.py` and modify:
```python
await tester.test_chat_endpoint("Your custom query here")
```

### Test Specific Features
Comment out tests you don't need in the `run_all_tests()` method.

### Integration with pytest
You can also use the existing pytest tests:
```powershell
pytest tests/e2e_agents_test.py -v
pytest tests/test_app.py -v
```

## Next Steps

1. **Run the test suite** to verify everything works
2. **Check the summary** to see what passed/failed
3. **Fix any issues** based on the test results
4. **Re-run tests** to verify fixes

## Continuous Testing

For CI/CD, you can run:
```powershell
python tests/test_functionality.py --backend-url $BACKEND_URL --agents-url $AGENTS_URL
```

Exit code 0 = all tests passed
Exit code 1 = some tests failed

