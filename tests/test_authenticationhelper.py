import pytest

from core.authentication import AuthenticationHelper, AuthError


def create_authentication_helper():
    return AuthenticationHelper(
        use_authentication=True,
        server_app_id="SERVER_APP",
        server_app_secret="SERVER_SECRET",
        client_app_id="CLIENT_APP",
        tenant_id="TENANT_ID",
        token_cache_path=None,
    )


@pytest.mark.asyncio
async def test_get_auth_claims_success(mock_confidential_client_success):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert auth_claims.get("oid") == "OID_X"
    assert auth_claims.get("groups") == ["GROUP_Y", "GROUP_Z"]


@pytest.mark.asyncio
async def test_get_auth_claims_unauthorized(mock_confidential_client_unauthorized):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert len(auth_claims.keys()) == 0


@pytest.mark.asyncio
async def test_get_auth_claims_overage_success(mock_confidential_client_overage, mock_list_groups_success):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert auth_claims.get("oid") == "OID_X"
    assert auth_claims.get("groups") == ["OVERAGE_GROUP_Y", "OVERAGE_GROUP_Z"]


@pytest.mark.asyncio
async def test_get_auth_claims_overage_unauthorized(mock_confidential_client_overage, mock_list_groups_unauthorized):
    helper = create_authentication_helper()
    auth_claims = await helper.get_auth_claims_if_enabled(headers={"Authorization": "Bearer Token"})
    assert len(auth_claims.keys()) == 0


@pytest.mark.asyncio
async def test_list_groups_success(mock_list_groups_success):
    groups = await AuthenticationHelper.list_groups(graph_resource_access_token={"access_token": "MockToken"})
    assert groups == ["OVERAGE_GROUP_Y", "OVERAGE_GROUP_Z"]


@pytest.mark.asyncio
async def test_list_groups_unauthorized(mock_list_groups_unauthorized):
    with pytest.raises(AuthError) as exc_info:
        await AuthenticationHelper.list_groups(graph_resource_access_token={"access_token": "MockToken"})
    assert exc_info.value.error == '{"error": "unauthorized"}'
