import base64
import json
import re
from datetime import datetime, timedelta, timezone

import aiohttp
import jwt
import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.models import SearchField, SearchIndex
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from core.authentication import AuthenticationHelper, AuthError

from .mocks import MockAsyncPageIterator, MockResponse

MockSearchIndex = SearchIndex(
    name="test",
    fields=[
        SearchField(name="oids", type="Collection(Edm.String)"),
        SearchField(name="groups", type="Collection(Edm.String)"),
    ],
)


def create_authentication_helper(
    require_access_control: bool = False,
    enable_global_documents: bool = False,
    enable_unauthenticated_access: bool = False,
):
    return AuthenticationHelper(
        search_index=MockSearchIndex,
        use_authentication=True,
        server_app_id="SERVER_APP",
        server_app_secret="SERVER_SECRET",
        client_app_id="CLIENT_APP",
        tenant_id="TENANT_ID",
        require_access_control=require_access_control,
        enable_global_documents=enable_global_documents,
        enable_unauthenticated_access=enable_unauthenticated_access,
    )


def create_search_client():
    return SearchClient(endpoint="", index_name="", credential=AzureKeyCredential(""))


def create_mock_jwt(kid="mock_kid", oid="OID_X"):
    # Create a payload with necessary claims
    payload = {
        "iss": "https://login.microsoftonline.com/TENANT_ID/v2.0",
        "sub": "AaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaA",
        "aud": "SERVER_APP",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "nbf": int(datetime.now(timezone.utc).timestamp()),
        "name": "John Doe",
        "oid": oid,
        "preferred_username": "john.doe@example.com",
        "rh": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.",
        "tid": "22222222-2222-2222-2222-222222222222",
        "uti": "AbCdEfGhIjKlMnOp-ABCDEFG",
        "ver": "2.0",
    }

    # Create a header
    header = {"kid": kid, "alg": "RS256", "typ": "JWT"}

    # Create a mock private key (for signing)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Create the JWT
    token = jwt.encode(payload, private_key, algorithm="RS256", headers=header)

    return token, private_key.public_key(), payload


@pytest.mark.asyncio
async def test_get_auth_claims_success(mock_confidential_client_success, mock_validate_token_success):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert auth_claims.get("oid") == "OID_X"
    assert auth_claims.get("groups") == ["GROUP_Y", "GROUP_Z"]


@pytest.mark.asyncio
async def test_get_auth_claims_unauthorized(mock_confidential_client_unauthorized, mock_validate_token_success):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert len(auth_claims.keys()) == 0


@pytest.mark.asyncio
async def test_get_auth_claims_overage_success(
    mock_confidential_client_overage, mock_list_groups_success, mock_validate_token_success
):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert auth_claims.get("oid") == "OID_X"
    assert auth_claims.get("groups") == ["OVERAGE_GROUP_Y", "OVERAGE_GROUP_Z"]


@pytest.mark.asyncio
async def test_get_auth_claims_overage_unauthorized(
    mock_confidential_client_overage, mock_list_groups_unauthorized, mock_validate_token_success
):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert len(auth_claims.keys()) == 0


@pytest.mark.asyncio
async def test_list_groups_success(mock_list_groups_success, mock_validate_token_success):
    groups = await AuthenticationHelper.list_groups(graph_resource_access_token={"access_token": "MockToken"})
    assert groups == ["OVERAGE_GROUP_Y", "OVERAGE_GROUP_Z"]


@pytest.mark.asyncio
async def test_list_groups_unauthorized(mock_list_groups_unauthorized, mock_validate_token_success):
    with pytest.raises(AuthError) as exc_info:
        await AuthenticationHelper.list_groups(graph_resource_access_token={"access_token": "MockToken"})
    assert exc_info.value.error == '{"error": "unauthorized"}'


def test_auth_setup(mock_confidential_client_success, mock_validate_token_success, snapshot):
    helper = create_authentication_helper()
    result = helper.get_auth_setup_for_client()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


def test_auth_setup_required_access_control(mock_confidential_client_success, mock_validate_token_success, snapshot):
    helper = create_authentication_helper(require_access_control=True)
    result = helper.get_auth_setup_for_client()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


def test_auth_setup_required_access_control_and_unauthenticated_access(
    mock_confidential_client_success, mock_validate_token_success, snapshot
):
    helper = create_authentication_helper(require_access_control=True, enable_unauthenticated_access=True)
    result = helper.get_auth_setup_for_client()
    snapshot.assert_match(json.dumps(result, indent=4), "result.json")


def test_get_auth_token(mock_confidential_client_success, mock_validate_token_success):
    with pytest.raises(AuthError) as exc_info:
        AuthenticationHelper.get_token_auth_header({})
    assert exc_info.value.status_code == 401
    with pytest.raises(AuthError) as exc_info:
        AuthenticationHelper.get_token_auth_header({"Authorization": ". ."})
    assert exc_info.value.status_code == 401
    with pytest.raises(AuthError) as exc_info:
        AuthenticationHelper.get_token_auth_header({"Authorization": "invalid"})
    assert exc_info.value.status_code == 401
    with pytest.raises(AuthError) as exc_info:
        AuthenticationHelper.get_token_auth_header({"Authorization": "invalid MockToken"})
    assert exc_info.value.status_code == 401
    assert AuthenticationHelper.get_token_auth_header({"Authorization": "Bearer MockToken"}) == "MockToken"
    AuthenticationHelper.get_token_auth_header({"x-ms-token-aad-access-token": "MockToken"}) == "MockToken"


def test_build_security_filters(mock_confidential_client_success, mock_validate_token_success):
    auth_helper = create_authentication_helper()
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    auth_helper_enable_global_documents = create_authentication_helper(enable_global_documents=True)
    auth_helper_require_access_control_and_enable_global_documents = create_authentication_helper(
        require_access_control=True, enable_global_documents=True
    )
    auth_helper_all_options = create_authentication_helper(
        require_access_control=True, enable_global_documents=True, enable_unauthenticated_access=True
    )
    assert auth_helper.build_security_filters(overrides={}, auth_claims={}) is None
    assert (
        auth_helper_require_access_control.build_security_filters(overrides={}, auth_claims={})
        == "(oids/any(g:search.in(g, '')) or groups/any(g:search.in(g, '')))"
    )
    assert (
        auth_helper.build_security_filters(overrides={"use_oid_security_filter": True}, auth_claims={"oid": "OID_X"})
        == "oids/any(g:search.in(g, 'OID_X'))"
    )
    assert (
        auth_helper_require_access_control.build_security_filters(overrides={}, auth_claims={"oid": "OID_X"})
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, '')))"
    )
    assert (
        auth_helper.build_security_filters(
            overrides={"use_groups_security_filter": True}, auth_claims={"groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))"
    )
    assert (
        auth_helper_require_access_control.build_security_filters(
            overrides={}, auth_claims={"groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "(oids/any(g:search.in(g, '')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    assert (
        auth_helper.build_security_filters(
            overrides={"use_oid_security_filter": True, "use_groups_security_filter": True},
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
        )
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    assert (
        auth_helper_require_access_control.build_security_filters(
            overrides={},
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
        )
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    assert (
        auth_helper.build_security_filters(overrides={"use_groups_security_filter": True}, auth_claims={"oid": "OID_X"})
        == "groups/any(g:search.in(g, ''))"
    )
    assert (
        auth_helper.build_security_filters(
            overrides={"use_oid_security_filter": True}, auth_claims={"groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "oids/any(g:search.in(g, ''))"
    )
    assert auth_helper.build_security_filters(overrides={}, auth_claims={}) is None
    assert auth_helper_enable_global_documents.build_security_filters(overrides={}, auth_claims={}) is None
    assert (
        auth_helper_enable_global_documents.build_security_filters(
            overrides={"use_oid_security_filter": True, "use_groups_security_filter": True},
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
        )
        == "((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_enable_global_documents.build_security_filters(
            overrides={"use_oid_security_filter": True}, auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "(oids/any(g:search.in(g, 'OID_X')) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_enable_global_documents.build_security_filters(
            overrides={"use_groups_security_filter": True},
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
        )
        == "(groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_require_access_control_and_enable_global_documents.build_security_filters(
            overrides={}, auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_require_access_control_and_enable_global_documents.build_security_filters(
            overrides={}, auth_claims={}
        )
        == "((oids/any(g:search.in(g, '')) or groups/any(g:search.in(g, ''))) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_all_options.build_security_filters(
            overrides={}, auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any()))"
    )
    assert (
        auth_helper_all_options.build_security_filters(overrides={}, auth_claims={})
        == "((oids/any(g:search.in(g, '')) or groups/any(g:search.in(g, ''))) or (not oids/any() and not groups/any()))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_denied(monkeypatch, mock_confidential_client_success, mock_validate_token_success):
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control.check_path_auth(
            path="Benefit_Options-2.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is False
    )
    assert (
        filter
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) and ((sourcefile eq 'Benefit_Options-2.pdf') or (sourcepage eq 'Benefit_Options-2.pdf'))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_allowed_sourcepage(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcepage": "Benefit_Options-2.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control.check_path_auth(
            path="Benefit_Options-2's complement.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert (
        filter
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) and ((sourcefile eq 'Benefit_Options-2''s complement.pdf') or (sourcepage eq 'Benefit_Options-2''s complement.pdf'))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_allowed_sourcefile(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcefile": "Benefit_Options.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control.check_path_auth(
            path="Benefit_Options.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert (
        filter
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) and ((sourcefile eq 'Benefit_Options.pdf') or (sourcepage eq 'Benefit_Options.pdf'))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_allowed_public_sourcefile(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control_and_enable_global_documents = create_authentication_helper(
        require_access_control=True, enable_global_documents=True
    )
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcefile": "Benefit_Options.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control_and_enable_global_documents.check_path_auth(
            path="Benefit_Options.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert (
        filter
        == "((oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) or (not oids/any() and not groups/any())) and ((sourcefile eq 'Benefit_Options.pdf') or (sourcepage eq 'Benefit_Options.pdf'))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_allowed_empty(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcefile": "Benefit_Options.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control.check_path_auth(
            path="",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert filter is None


@pytest.mark.asyncio
async def test_check_path_auth_allowed_public_empty(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control_and_enable_global_documents = create_authentication_helper(
        require_access_control=True, enable_global_documents=True
    )
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcefile": "Benefit_Options.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control_and_enable_global_documents.check_path_auth(
            path="",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert filter is None


@pytest.mark.asyncio
async def test_check_path_auth_allowed_fragment(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control = create_authentication_helper(require_access_control=True)
    filter = None

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        filter = kwargs.get("filter")
        return MockAsyncPageIterator(data=[{"sourcefile": "Benefit_Options.pdf"}])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control.check_path_auth(
            path="Benefit_Options.pdf#textafterfragment",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert (
        filter
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))) and ((sourcefile eq 'Benefit_Options.pdf') or (sourcepage eq 'Benefit_Options.pdf'))"
    )


@pytest.mark.asyncio
async def test_check_path_auth_allowed_without_access_control(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper = create_authentication_helper(require_access_control=False)
    filter = None
    called_search = False

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        nonlocal called_search
        filter = kwargs.get("filter")
        called_search = True
        return MockAsyncPageIterator(data=[])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper.check_path_auth(
            path="Benefit_Options-2.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert filter is None
    assert called_search is False


@pytest.mark.asyncio
async def test_check_path_auth_allowed_public_without_access_control(
    monkeypatch, mock_confidential_client_success, mock_validate_token_success
):
    auth_helper_require_access_control_and_enable_global_documents = create_authentication_helper(
        require_access_control=False, enable_global_documents=True
    )
    filter = None
    called_search = False

    async def mock_search(self, *args, **kwargs):
        nonlocal filter
        nonlocal called_search
        filter = kwargs.get("filter")
        called_search = True
        return MockAsyncPageIterator(data=[])

    monkeypatch.setattr(SearchClient, "search", mock_search)

    assert (
        await auth_helper_require_access_control_and_enable_global_documents.check_path_auth(
            path="Benefit_Options-2.pdf",
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
            search_client=create_search_client(),
        )
        is True
    )
    assert filter is None
    assert called_search is False


@pytest.mark.asyncio
async def test_create_pem_format(mock_confidential_client_success, mock_validate_token_success):
    helper = create_authentication_helper()
    mock_token, public_key, payload = create_mock_jwt(oid="OID_X")
    _, other_public_key, _ = create_mock_jwt(oid="OID_Y")
    mock_jwks = {
        "keys": [
            # Include a key with a different KID to ensure the correct key is selected
            {
                "kty": "RSA",
                "kid": "other_mock_kid",
                "use": "sig",
                "n": base64.urlsafe_b64encode(
                    other_public_key.public_numbers().n.to_bytes(
                        (other_public_key.public_numbers().n.bit_length() + 7) // 8, byteorder="big"
                    )
                )
                .decode("utf-8")
                .rstrip("="),
                "e": base64.urlsafe_b64encode(
                    other_public_key.public_numbers().e.to_bytes(
                        (other_public_key.public_numbers().e.bit_length() + 7) // 8, byteorder="big"
                    )
                )
                .decode("utf-8")
                .rstrip("="),
            },
            {
                "kty": "RSA",
                "kid": "mock_kid",
                "use": "sig",
                "n": base64.urlsafe_b64encode(
                    public_key.public_numbers().n.to_bytes(
                        (public_key.public_numbers().n.bit_length() + 7) // 8, byteorder="big"
                    )
                )
                .decode("utf-8")
                .rstrip("="),
                "e": base64.urlsafe_b64encode(
                    public_key.public_numbers().e.to_bytes(
                        (public_key.public_numbers().e.bit_length() + 7) // 8, byteorder="big"
                    )
                )
                .decode("utf-8")
                .rstrip("="),
            },
        ]
    }

    pem_key = await helper.create_pem_format(mock_jwks, mock_token)

    # Assert that the result is bytes
    assert isinstance(pem_key, bytes), "create_pem_format should return bytes"

    # Convert bytes to string for regex matching
    pem_str = pem_key.decode("utf-8")

    # Assert that the key starts and ends with the correct markers
    assert pem_str.startswith("-----BEGIN PUBLIC KEY-----"), "PEM key should start with the correct marker"
    assert pem_str.endswith("-----END PUBLIC KEY-----\n"), "PEM key should end with the correct marker"

    # Assert that the format matches the structure of a PEM key
    pem_regex = r"^-----BEGIN PUBLIC KEY-----\n([A-Za-z0-9+/\n]+={0,2})\n-----END PUBLIC KEY-----\n$"
    assert re.match(pem_regex, pem_str), "PEM key format is incorrect"

    # Verify that the key can be used to decode the token
    try:
        decoded = jwt.decode(
            mock_token, key=pem_key, algorithms=["RS256"], audience=payload["aud"], issuer=payload["iss"]
        )
        assert decoded["oid"] == payload["oid"], "Decoded token should contain correct OID"
    except Exception as e:
        pytest.fail(f"jwt.decode raised an unexpected exception: {str(e)}")

    # Try to load the key using cryptography library to ensure it's a valid PEM format
    try:
        loaded_public_key = serialization.load_pem_public_key(pem_key)
        assert isinstance(loaded_public_key, rsa.RSAPublicKey), "Loaded key should be an RSA public key"
    except Exception as e:
        pytest.fail(f"Failed to load PEM key: {str(e)}")


@pytest.mark.asyncio
async def test_validate_access_token(monkeypatch, mock_confidential_client_success):
    mock_token, public_key, payload = create_mock_jwt(oid="OID_X")

    def mock_get(*args, **kwargs):
        return MockResponse(
            status=200,
            text=json.dumps(
                {
                    "keys": [
                        {
                            "kty": "RSA",
                            "use": "sig",
                            "kid": "23nt",
                            "x5t": "23nt",
                            "n": "hu2SJ",
                            "e": "AQAB",
                            "x5c": ["MIIC/jCC"],
                            "issuer": "https://login.microsoftonline.com/TENANT_ID/v2.0",
                        },
                        {
                            "kty": "RSA",
                            "use": "sig",
                            "kid": "MGLq",
                            "x5t": "MGLq",
                            "n": "yfNcG8",
                            "e": "AQAB",
                            "x5c": ["MIIC/jCC"],
                            "issuer": "https://login.microsoftonline.com/TENANT_ID/v2.0",
                        },
                    ]
                }
            ),
        )

    monkeypatch.setattr(aiohttp.ClientSession, "get", mock_get)

    def mock_decode(*args, **kwargs):
        return payload

    monkeypatch.setattr(jwt, "decode", mock_decode)

    async def mock_create_pem_format(*args, **kwargs):
        return public_key

    monkeypatch.setattr(AuthenticationHelper, "create_pem_format", mock_create_pem_format)

    helper = create_authentication_helper()
    await helper.validate_access_token(mock_token)
