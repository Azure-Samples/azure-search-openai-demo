import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.core.exceptions import HttpResponseError
from azure.search.documents.indexes.models import (
    AIServicesAccountIdentity,
    AzureOpenAIEmbeddingSkill,
    ConditionalSkill,
    ContentUnderstandingSkill,
    IndexerExecutionResult,
    IndexerExecutionStatus,
    MergeSkill,
    PermissionFilter,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexerDataSourceType,
    SearchIndexerError,
    SearchIndexerStatus,
    SearchIndexerWarning,
    SimpleField,
)

from prepdocslib.builtincloudingestionstrategy import (
    BuiltInCloudIngestionStrategy,
    check_acl_ingestion,
    validate_acl_configuration,
    wait_for_indexer,
)
from prepdocslib.embeddings import OpenAIEmbeddings
from prepdocslib.strategy import SearchInfo

from .mocks import MockAzureCredential

CU_ENDPOINT = "https://cu-test.cognitiveservices.azure.com/"


def create_strategy(use_acls: bool = False) -> BuiltInCloudIngestionStrategy:
    blob_manager = MagicMock()
    blob_manager.container = "content"
    blob_manager.get_managedidentity_connectionstring.return_value = "ResourceId=/subscriptions/sub/storage;"
    return BuiltInCloudIngestionStrategy(
        list_file_strategy=MagicMock(),
        blob_manager=blob_manager,
        search_info=SearchInfo(
            endpoint="https://test.search.windows.net", credential=MockAzureCredential(), index_name="gptkbindex"
        ),
        embeddings=OpenAIEmbeddings(
            open_ai_client=MagicMock(),
            open_ai_model_name="text-embedding-3-large",
            open_ai_dimensions=3072,
            azure_deployment_name="emb-deployment",
            azure_endpoint="https://openai-test.openai.azure.com/",
        ),
        search_field_name_embedding="embedding3",
        content_understanding_endpoint=CU_ENDPOINT,
        use_acls=use_acls,
    )


def projection_mappings(strategy: BuiltInCloudIngestionStrategy) -> dict[str, str]:
    index_projection = strategy.build_skillset().index_projection
    assert index_projection is not None
    return {mapping.name: mapping.source for mapping in index_projection.selectors[0].mappings}


def test_build_skillset_uses_only_builtin_skills():
    strategy = create_strategy()
    skillset = strategy.build_skillset()

    assert skillset.name == "gptkbindex-cloud-skillset"
    content_understanding, page_citation, sourcepage, embedding = skillset.skills
    assert isinstance(content_understanding, ContentUnderstandingSkill)
    assert content_understanding.extraction_options == ["locationMetadata"]
    assert "modelName" not in content_understanding and "modelDeployment" not in content_understanding
    assert isinstance(embedding, AzureOpenAIEmbeddingSkill)
    assert embedding.deployment_name == "emb-deployment"
    assert embedding.dimensions == 3072
    assert isinstance(skillset.cognitive_services_account, AIServicesAccountIdentity)
    assert skillset.cognitive_services_account.subdomain_url == CU_ENDPOINT

    # Page citations: Merge appends the page number to the file name, Conditional applies it only to PDFs
    assert isinstance(page_citation, MergeSkill)
    assert page_citation.insert_pre_tag == "#page="
    assert page_citation.insert_post_tag == ""
    merge_inputs = {i.name: i.source for i in page_citation.inputs}
    assert merge_inputs["text"] == "/document/metadata_storage_name"
    assert merge_inputs["itemsToInsert"] == "=[$(/document/text_sections/*/locationMetadata/pageNumberFrom)]"
    assert isinstance(sourcepage, ConditionalSkill)
    condition_inputs = {i.name: i.source for i in sourcepage.inputs}
    assert "'.pdf'" in condition_inputs["condition"] and "'.PDF'" in condition_inputs["condition"]
    assert "pageNumberFrom) > 0" in condition_inputs["condition"]
    assert condition_inputs["whenFalse"] == "/document/metadata_storage_name"

    mappings = projection_mappings(strategy)
    assert mappings["sourcepage"] == "/document/text_sections/*/sourcepage"
    assert mappings["embedding3"] == "/document/text_sections/*/embedding"
    assert "oids" not in mappings and "groups" not in mappings

    data_source = strategy.build_data_source()
    assert data_source.type == SearchIndexerDataSourceType.AZURE_BLOB
    assert data_source.indexer_permission_options is None

    indexer = strategy.build_indexer()
    assert indexer.skillset_name == "gptkbindex-cloud-skillset"
    assert indexer.parameters.configuration.allow_skillset_to_read_file_data is True


def test_build_skillset_with_acls_uses_native_permissions():
    strategy = create_strategy(use_acls=True)

    mappings = projection_mappings(strategy)
    assert mappings["oids"] == "/document/metadata_user_ids"
    assert mappings["groups"] == "/document/metadata_group_ids"
    assert mappings["metadata_storage_path"] == "/document/metadata_storage_path"

    data_source = strategy.build_data_source()
    assert data_source.type == SearchIndexerDataSourceType.ADLS_GEN2
    # The option is set after construction, so check that it's in the request body sent to the service
    assert data_source.as_dict()["indexerPermissionOptions"] == ["userIds", "groupIds"]


def acl_index(oids_filter=PermissionFilter.USER_IDS, include_storage_path=True) -> SearchIndex:
    fields = [
        SimpleField(name="id", type="Edm.String", key=True),
        SearchField(
            name="oids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            permission_filter=oids_filter,
        ),
        SearchField(
            name="groups",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            permission_filter=PermissionFilter.GROUP_IDS,
        ),
    ]
    if include_storage_path:
        fields.append(SimpleField(name="metadata_storage_path", type="Edm.String", filterable=True))
    return SearchIndex(name="gptkbindex", fields=fields)


def test_validate_acl_configuration_accepts_valid_configuration():
    data_source = create_strategy(use_acls=True).build_data_source()
    validate_acl_configuration(data_source, acl_index())


def test_validate_acl_configuration_reports_every_problem():
    data_source = create_strategy(use_acls=False).build_data_source()
    index = acl_index(oids_filter=None, include_storage_path=False)

    with pytest.raises(ValueError) as exc_info:
        validate_acl_configuration(data_source, index)

    message = str(exc_info.value)
    assert "not 'adlsgen2'" in message
    assert "expected userIds and groupIds" in message
    assert "'oids' is missing or doesn't have permissionFilter" in message
    assert "'metadata_storage_path' is missing" in message


def search_client_with_counts(total: int, missing: int, no_access: int = 0) -> MagicMock:
    async def search(**kwargs):
        results = MagicMock()
        filter = kwargs.get("filter")
        if filter is None:
            count = total
        elif "'none'" in filter:
            count = no_access
        else:
            count = missing
        results.get_count = AsyncMock(return_value=count)
        return results

    search_client = MagicMock()
    search_client.search = AsyncMock(side_effect=search)
    return search_client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "total, missing, no_access, level, expected",
    [
        (6, 6, 0, logging.ERROR, "None of the 6 indexed chunks have permissions"),
        (6, 2, 0, logging.WARNING, "2 of 6 indexed chunks have no permissions"),
        (6, 0, 4, logging.WARNING, "4 of 6 indexed chunks are from files without named user or group ACL entries"),
        (6, 0, 0, logging.INFO, "All 6 indexed chunks have permissions"),
    ],
)
async def test_check_acl_ingestion(caplog, total, missing, no_access, level, expected):
    search_client = search_client_with_counts(total, missing, no_access)

    with caplog.at_level(logging.INFO, logger="scripts"):
        await check_acl_ingestion(search_client, use_elevated_read=True)

    assert any(record.levelno == level and expected in record.getMessage() for record in caplog.records)
    for call in search_client.search.await_args_list:
        assert call.kwargs["enable_elevated_read"] is True


@pytest.mark.asyncio
async def test_check_acl_ingestion_warns_when_check_fails(caplog):
    search_client = MagicMock()
    search_client.search = AsyncMock(side_effect=HttpResponseError(message="missing elevated read permission"))

    with caplog.at_level(logging.WARNING, logger="scripts"):
        await check_acl_ingestion(search_client, use_elevated_read=False)

    assert "Couldn't verify that permissions were ingested: missing elevated read permission" in caplog.text


def indexer_status(
    status: str, start_time: datetime, warnings=None, errors=None, error_message=None
) -> SearchIndexerStatus:
    return SearchIndexerStatus(
        last_result=IndexerExecutionResult(
            status=status,
            start_time=start_time,
            error_message=error_message,
            item_count=3,
            failed_item_count=len(errors or []),
            warnings=warnings or [],
            errors=errors or [],
        )
    )


@pytest.mark.asyncio
async def test_wait_for_indexer_logs_warnings_and_errors(caplog):
    previous_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    indexer_client = MagicMock()
    indexer_client.get_indexer_status = AsyncMock(
        side_effect=[
            indexer_status(IndexerExecutionStatus.SUCCESS, previous_start),
            indexer_status(IndexerExecutionStatus.IN_PROGRESS, new_start),
            indexer_status(
                IndexerExecutionStatus.SUCCESS,
                new_start,
                warnings=[SearchIndexerWarning(key="big.pdf", message="Document exceeds the 16 MB limit")],
                errors=[SearchIndexerError(key="bad.pdf", error_message="Could not parse", status_code=400)],
                error_message="Data source is not accessible",
            ),
        ]
    )

    with caplog.at_level(logging.INFO, logger="scripts"):
        finished = await wait_for_indexer(indexer_client, "test-indexer", previous_start, poll_interval_seconds=0)

    assert finished is True
    assert indexer_client.get_indexer_status.await_count == 3
    assert "Indexer warning for 'big.pdf': Document exceeds the 16 MB limit" in caplog.text
    assert "Indexer error for 'bad.pdf': Could not parse" in caplog.text
    assert "Indexer 'test-indexer' run error: Data source is not accessible" in caplog.text


@pytest.mark.asyncio
async def test_wait_for_indexer_times_out(caplog, monkeypatch):
    monkeypatch.setattr("prepdocslib.builtincloudingestionstrategy.asyncio.sleep", AsyncMock())
    indexer_client = MagicMock()
    indexer_client.get_indexer_status = AsyncMock(
        return_value=indexer_status(IndexerExecutionStatus.IN_PROGRESS, datetime(2026, 1, 2, tzinfo=timezone.utc))
    )

    with caplog.at_level(logging.WARNING, logger="scripts"):
        finished = await wait_for_indexer(
            indexer_client, "test-indexer", None, poll_interval_seconds=1, timeout_seconds=2
        )

    assert finished is False

    assert "still running" in caplog.text


@pytest.fixture
def cloud_ingestion_env(monkeypatch):
    for key, value in {
        "AZURE_SEARCH_SERVICE": "test-search",
        "AZURE_SEARCH_INDEX": "gptkbindex",
        "AZURE_STORAGE_ACCOUNT": "teststorage",
        "AZURE_STORAGE_CONTAINER": "content",
        "AZURE_STORAGE_RESOURCE_GROUP": "test-rg",
        "AZURE_SUBSCRIPTION_ID": "test-sub",
        "AZURE_SEARCH_FIELD_NAME_EMBEDDING": "embedding3",
        "OPENAI_HOST": "azure",
        "AZURE_OPENAI_SERVICE": "test-openai",
        "AZURE_OPENAI_EMB_MODEL_NAME": "text-embedding-3-large",
        "AZURE_OPENAI_EMB_DEPLOYMENT": "emb-deployment",
        "AZURE_OPENAI_EMB_DIMENSIONS": "3072",
        "AZURE_CONTENTUNDERSTANDING_ENDPOINT": CU_ENDPOINT,
        "USE_CLOUD_INGESTION_BUILTIN": "true",
    }.items():
        monkeypatch.setenv(key, value)
    for key in [
        "USE_MULTIMODAL",
        "USE_CLOUD_INGESTION_ACLS",
        "AZURE_CLOUD_INGESTION_STORAGE_ACCOUNT",
        "USE_MEDIA_DESCRIBER_AZURE_CU",
        "AZURE_CONTENTUNDERSTANDING_DEPLOYMENT",
        "AZURE_CONTENTUNDERSTANDING_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.asyncio
async def test_setup_cloud_ingestion_strategy_selects_builtin(cloud_ingestion_env):
    from setup_cloud_ingestion import setup_cloud_ingestion_strategy

    strategy, openai_client, _, blob_manager = await setup_cloud_ingestion_strategy(MockAzureCredential())
    try:
        assert isinstance(strategy, BuiltInCloudIngestionStrategy)
        assert strategy.content_understanding_endpoint == CU_ENDPOINT
        assert strategy.use_acls is False
    finally:
        await blob_manager.close_clients()
        await openai_client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "env, expected",
    [
        ({"USE_MEDIA_DESCRIBER_AZURE_CU": "false", "AZURE_CONTENTUNDERSTANDING_DEPLOYMENT": "gpt-dep"}, None),
        (
            {"USE_MEDIA_DESCRIBER_AZURE_CU": "true", "AZURE_CONTENTUNDERSTANDING_DEPLOYMENT": "gpt-dep"},
            ("gpt-dep", "gpt-dep"),
        ),
        (
            {
                "USE_MEDIA_DESCRIBER_AZURE_CU": "true",
                "AZURE_CONTENTUNDERSTANDING_DEPLOYMENT": "gpt-dep",
                "AZURE_CONTENTUNDERSTANDING_MODEL": "gpt-model",
            },
            ("gpt-model", "gpt-dep"),
        ),
    ],
)
async def test_setup_cloud_ingestion_strategy_builtin_figure_descriptions(
    cloud_ingestion_env, monkeypatch, env, expected
):
    from setup_cloud_ingestion import setup_cloud_ingestion_strategy

    for key, value in env.items():
        monkeypatch.setenv(key, value)
    strategy, openai_client, _, blob_manager = await setup_cloud_ingestion_strategy(MockAzureCredential())
    try:
        assert isinstance(strategy, BuiltInCloudIngestionStrategy)
        skill = strategy.build_skillset().skills[0]
        if expected is None:
            assert "modelName" not in skill
        else:
            assert (skill["modelName"], skill["modelDeployment"]) == expected
    finally:
        await blob_manager.close_clients()
        await openai_client.close()


@pytest.mark.asyncio
async def test_setup_cloud_ingestion_strategy_builtin_rejects_multimodal(cloud_ingestion_env, monkeypatch):
    from setup_cloud_ingestion import setup_cloud_ingestion_strategy

    monkeypatch.setenv("USE_MULTIMODAL", "true")
    with pytest.raises(ValueError, match="does not support USE_MULTIMODAL"):
        await setup_cloud_ingestion_strategy(MockAzureCredential())


@pytest.mark.asyncio
async def test_setup_cloud_ingestion_strategy_selects_custom_functions(cloud_ingestion_env, monkeypatch):
    from prepdocslib.cloudingestionstrategy import CloudIngestionStrategy
    from setup_cloud_ingestion import setup_cloud_ingestion_strategy

    monkeypatch.setenv("USE_CLOUD_INGESTION_BUILTIN", "false")
    monkeypatch.setenv("AZURE_SEARCH_USER_ASSIGNED_IDENTITY_RESOURCE_ID", "/subscriptions/sub/identity")
    for skill in ["DOCUMENT_EXTRACTOR", "FIGURE_PROCESSOR", "TEXT_PROCESSOR"]:
        monkeypatch.setenv(f"{skill}_SKILL_ENDPOINT", f"https://{skill.lower()}.azurewebsites.net/api/process")
        monkeypatch.setenv(f"{skill}_SKILL_AUTH_RESOURCE_ID", f"api://{skill.lower()}")

    strategy, openai_client, _, blob_manager = await setup_cloud_ingestion_strategy(MockAzureCredential())
    try:
        assert isinstance(strategy, CloudIngestionStrategy)
        assert strategy.text_processor.uri == "https://text_processor.azurewebsites.net/api/process"
    finally:
        await blob_manager.close_clients()
        await openai_client.close()
