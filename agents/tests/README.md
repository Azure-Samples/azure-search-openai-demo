# Microsoft 365 RAG Agent Tests

This directory contains comprehensive pytest-based tests for the Microsoft 365 RAG Agent.

## Test Structure

### Test Files

- **`test_teams_components.py`** - Tests for Teams UI components and Adaptive Cards
- **`test_teams_response_adapter.py`** - Tests for Teams response formatting and adaptation
- **`test_teams_handler.py`** - Tests for Teams message handling and adaptive card actions

### Test Categories

- **Unit Tests** - Test individual components in isolation with mocks
- **Integration Tests** - Test component interactions (marked with `@pytest.mark.integration`)
- **Async Tests** - Test asynchronous functionality with `@pytest.mark.asyncio`

## Running Tests

### Prerequisites

Install the required testing dependencies:

```bash
# Using system packages (Ubuntu/Debian)
sudo apt install python3-pytest python3-pytest-asyncio python3-pytest-cov python3-pytest-mock

# Or using pip (if virtual environment is available)
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Running All Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run specific test file
python3 -m pytest tests/test_teams_components.py -v

# Run specific test
python3 -m pytest tests/test_teams_components.py::TestTeamsComponents::test_create_welcome_card -v
```

### Test Configuration

The tests use `pytest.ini` for configuration:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --asyncio-mode=auto
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    unit: marks tests as unit tests
    slow: marks tests as slow running
```

## Test Design Principles

### 1. **No External Dependencies**
- All tests use mocks instead of hitting real Azure services
- No network calls or external API dependencies
- Tests run fast and reliably in any environment

### 2. **Comprehensive Coverage**
- Test all public methods and edge cases
- Test error handling and exception scenarios
- Test both success and failure paths

### 3. **Proper Async Testing**
- Use `@pytest.mark.asyncio` for async test methods
- Properly await async methods in tests
- Mock async dependencies correctly

### 4. **Mock Strategy**
- Mock external dependencies (RAG service, auth service, etc.)
- Use `unittest.mock.Mock` and `unittest.mock.patch`
- Create realistic mock data that matches expected interfaces

## Example Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from components.teams_components import TeamsComponents

class TestTeamsComponents:
    """Test cases for TeamsComponents."""
    
    def test_create_welcome_card(self):
        """Test welcome card creation."""
        card = TeamsComponents.create_welcome_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0
    
    @pytest.mark.asyncio
    async def test_async_method(self, mock_dependency):
        """Test async method with mocked dependency."""
        with patch.object(mock_dependency, 'method', return_value="test"):
            result = await some_async_method()
            assert result == "expected"
```

## Mock Data Patterns

### RAG Response Mock
```python
mock_rag_response = RAGResponse(
    answer="Test response",
    sources=[{"title": "Source 1", "url": "https://example.com"}],
    citations=["Citation 1"],
    thoughts=[{"title": "Thought 1", "description": "Description 1"}],
    token_usage={"total_tokens": 100},
    model_info={"model": "gpt-4"}
)
```

### Turn Context Mock
```python
class MockTurnContext:
    def __init__(self, activity: Activity):
        self.activity = activity
        self.channel_id = "msteams"
        self.conversation = activity.conversation
        self.from_property = activity.from_property
        self.recipient = Mock()
        self.recipient.id = "bot1"
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

- No external dependencies or network calls
- Fast execution (all tests complete in ~1-2 seconds)
- Reliable and deterministic results
- Proper error reporting and logging

## Coverage Goals

- **Unit Tests**: 100% coverage of core business logic
- **Integration Tests**: Cover all major component interactions
- **Error Handling**: Test all exception scenarios
- **Edge Cases**: Test boundary conditions and unusual inputs

## Debugging Tests

### Verbose Output
```bash
python3 -m pytest tests/ -v -s
```

### Stop on First Failure
```bash
python3 -m pytest tests/ -x
```

### Run Specific Test with Debug
```bash
python3 -m pytest tests/test_teams_components.py::TestTeamsComponents::test_create_welcome_card -v -s --tb=long
```

### Coverage Report
```bash
python3 -m pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```