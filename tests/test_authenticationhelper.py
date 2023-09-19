import msal
import pytest

from core.authentication import AuthenticationHelper


@pytest.fixture
def mock_confidential_client_success(monkeypatch):
    def mock_acquire_token_on_behalf_of(self, *args, **kwargs):
        assert kwargs.get("user_assertion") is not None
        scopes = kwargs.get("scopes")
        assert scopes == [AuthenticationHelper.scope]
        return {"access_token": "MockToken", "id_token_claims": {"oid": "XXX", "groups": ["YYY", "ZZZ"]}}

    monkeypatch.setattr(
        msal.ConfidentialClientApplication, "mock_acquire_token_on_behalf_of", mock_acquire_token_on_behalf_of
    )


def test_get_auth_claims_success(mock_confidential_client_success):
    pass
