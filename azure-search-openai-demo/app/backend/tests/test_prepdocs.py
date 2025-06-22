import pytest
from unittest.mock import AsyncMock, patch
from app.backend.prepdocs import setup_domain_classifier

@pytest.mark.asyncio
async def test_setup_domain_classifier():
    mock_openai_embeddings_service = AsyncMock()
    mock_search_index_client = AsyncMock()

    with patch('app.backend.prepdocslib.domain_classifier_setup.create_domain_classifier_index', return_value=None) as mock_create_index:
        await setup_domain_classifier(mock_openai_embeddings_service, mock_search_index_client)
        mock_create_index.assert_called_once()