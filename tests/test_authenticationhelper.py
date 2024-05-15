import json

import pytest
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.models import SearchField, SearchIndex

from core.authentication import AuthenticationHelper, AuthError

from .mocks import MockAsyncPageIterator

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
