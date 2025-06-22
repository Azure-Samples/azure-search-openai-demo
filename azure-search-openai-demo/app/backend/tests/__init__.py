from unittest import TestCase
from unittest.mock import patch, MagicMock
from app.backend.prepdocs import setup_domain_classifier

class TestSetupDomainClassifier(TestCase):
    @patch('app.backend.prepdocs.AzureSearchClient')
    @patch('app.backend.prepdocs.AzureDeveloperCliCredential')
    def test_setup_domain_classifier(self, mock_credential, mock_search_client):
        mock_token = MagicMock()
        mock_token.token = 'fake_token'
        mock_credential.return_value.get_token.return_value = mock_token
        
        mock_search_client.return_value.create_or_update_index.return_value = None
        
        result = setup_domain_classifier(mock_credential, mock_search_client)
        
        self.assertIsNone(result)
        mock_search_client.return_value.create_or_update_index.assert_called_once()