import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.search.documents.indexes.models import (
    AIServicesAccountIdentity,
    AzureOpenAIEmbeddingSkill,
    ConditionalSkill,
    ContentUnderstandingSkill,
    IndexerExecutionResult,
    IndexerExecutionStatus,
    MergeSkill,
    SearchIndexerDataSourceType,
    SearchIndexerError,
    SearchIndexerStatus,
    SearchIndexerWarning,
)

from prepdocslib.builtincloudingestionstrategy import (
    BuiltInCloudIngestionStrategy,
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


def test_build_skillset_with_acls_uses_native_permissions():
    strategy = create_strategy(use_acls=True)

    mappings = projection_mappings(strategy)
    assert mappings["oids"] == "/document/metadata_user_ids"
    assert mappings["groups"] == "/document/metadata_group_ids"
    assert mappings["metadata_storage_path"] == "/document/metadata_storage_path"

    data_source = strategy.build_data_source()
    assert data_source.type == SearchIndexerDataSourceType.ADLS_GEN2
    assert data_source.indexer_permission_options == ["userIds", "groupIds"]


def indexer_status(status: str, start_time: datetime, warnings=None, errors=None) -> SearchIndexerStatus:
    return SearchIndexerStatus(
        last_result=IndexerExecutionResult(
            status=status,
            start_time=start_time,
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
            ),
        ]
    )

    with caplog.at_level(logging.INFO, logger="scripts"):
        await wait_for_indexer(indexer_client, "test-indexer", previous_start, poll_interval_seconds=0)

    assert indexer_client.get_indexer_status.await_count == 3
    assert "Indexer warning for 'big.pdf': Document exceeds the 16 MB limit" in caplog.text
    assert "Indexer error for 'bad.pdf': Could not parse" in caplog.text


@pytest.mark.asyncio
async def test_wait_for_indexer_times_out(caplog, monkeypatch):
    monkeypatch.setattr("prepdocslib.builtincloudingestionstrategy.asyncio.sleep", AsyncMock())
    indexer_client = MagicMock()
    indexer_client.get_indexer_status = AsyncMock(
        return_value=indexer_status(IndexerExecutionStatus.IN_PROGRESS, datetime(2026, 1, 2, tzinfo=timezone.utc))
    )

    with caplog.at_level(logging.WARNING, logger="scripts"):
        await wait_for_indexer(indexer_client, "test-indexer", None, poll_interval_seconds=1, timeout_seconds=2)

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
    for key in ["USE_MULTIMODAL", "USE_CLOUD_INGESTION_ACLS", "AZURE_CLOUD_INGESTION_STORAGE_ACCOUNT"]:
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
async def test_setup_cloud_ingestion_strategy_builtin_rejects_multimodal(cloud_ingestion_env, monkeypatch):
    from setup_cloud_ingestion import setup_cloud_ingestion_strategy

    monkeypatch.setenv("USE_MULTIMODAL", "true")
    with pytest.raises(ValueError, match="does not support USE_MULTIMODAL"):
        await setup_cloud_ingestion_strategy(MockAzureCredential())
