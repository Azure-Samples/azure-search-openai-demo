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


def test_auth_setup(mock_confidential_client_success):
    helper = create_authentication_helper()
    assert helper.get_auth_setup_for_client() == {
        "useLogin": True,
        "msalConfig": {
            "auth": {
                "clientId": "CLIENT_APP",
                "authority": "https://login.microsoftonline.com/TENANT_ID",
                "redirectUri": "/redirect",
                "postLogoutRedirectUri": "/",
                "navigateToLoginRequestUrl": False,
            },
            "cache": {"cacheLocation": "sessionStorage", "storeAuthStateInCookie": False},
        },
        "loginRequest": {
            "scopes": [".default"],
        },
        "tokenRequest": {
            "scopes": ["api://SERVER_APP/access_as_user"],
        },
    }


def test_get_auth_token():
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


def test_build_security_filters():
    assert AuthenticationHelper.build_security_filters(overrides={}, auth_claims={}) is None
    assert (
        AuthenticationHelper.build_security_filters(
            overrides={"use_oid_security_filter": True}, auth_claims={"oid": "OID_X"}
        )
        == "oids/any(g:search.in(g, 'OID_X'))"
    )
    assert (
        AuthenticationHelper.build_security_filters(
            overrides={"use_groups_security_filter": True}, auth_claims={"groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z'))"
    )
    assert (
        AuthenticationHelper.build_security_filters(
            overrides={"use_oid_security_filter": True, "use_groups_security_filter": True},
            auth_claims={"oid": "OID_X", "groups": ["GROUP_Y", "GROUP_Z"]},
        )
        == "(oids/any(g:search.in(g, 'OID_X')) or groups/any(g:search.in(g, 'GROUP_Y, GROUP_Z')))"
    )
    assert (
        AuthenticationHelper.build_security_filters(
            overrides={"use_groups_security_filter": True}, auth_claims={"oid": "OID_X"}
        )
        == "groups/any(g:search.in(g, ''))"
    )
    assert (
        AuthenticationHelper.build_security_filters(
            overrides={"use_oid_security_filter": True}, auth_claims={"groups": ["GROUP_Y", "GROUP_Z"]}
        )
        == "oids/any(g:search.in(g, ''))"
    )
