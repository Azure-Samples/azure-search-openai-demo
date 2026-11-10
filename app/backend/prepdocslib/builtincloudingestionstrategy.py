"""Cloud ingestion strategy using only Azure AI Search built-in skills (no Azure Functions)."""

import asyncio
import logging
from datetime import datetime

from azure.core.exceptions import HttpResponseError
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexerClient
from azure.search.documents.indexes.models import (
    AIServicesAccountIdentity,
    AzureOpenAIEmbeddingSkill,
    ConditionalSkill,
    ContentUnderstandingSkill,
    ContentUnderstandingSkillChunkingProperties,
    ContentUnderstandingSkillChunkingUnit,
    ContentUnderstandingSkillExtractionOptions,
    IndexerExecutionStatus,
    IndexerPermissionOption,
    IndexingParameters,
    IndexingParametersConfiguration,
    IndexProjectionMode,
    InputFieldMappingEntry,
    MergeSkill,
    NativeBlobSoftDeleteDeletionDetectionPolicy,
    OutputFieldMappingEntry,
    PermissionFilter,
    SearchIndex,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataSourceType,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    SearchIndexerSkillset,
    SimpleField,
)

from .blobmanager import BlobManager
from .embeddings import OpenAIEmbeddings
from .listfilestrategy import ListFileStrategy
from .searchmanager import SearchManager
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")

CHUNK_MAX_CHARACTERS = 1000
CHUNK_OVERLAP_CHARACTERS = 100
INDEXER_POLL_INTERVAL_SECONDS = 15
INDEXER_POLL_TIMEOUT_SECONDS = 30 * 60

SECTIONS_CONTEXT = "/document/text_sections/*"
PAGE_NUMBER_SOURCE = f"{SECTIONS_CONTEXT}/locationMetadata/pageNumberFrom"
FILE_EXTENSION_SOURCE = "$(/document/metadata_storage_file_extension)"
METADATA_STORAGE_PATH_FIELD = "metadata_storage_path"


class BuiltInCloudIngestionStrategy(Strategy):
    """Ingestion strategy that uses an indexer with only built-in skills.

    Content Understanding extracts and chunks documents, Text Merge and Conditional skills build
    the ``sourcepage`` citation (``file.pdf#page=N`` for PDFs), and the Azure OpenAI Embedding skill
    vectorizes each chunk. When ``use_acls`` is enabled, the ADLS Gen2 data source ingests native
    file permissions into the ``oids`` and ``groups`` fields.
    """

    def __init__(
        self,
        *,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        embeddings: OpenAIEmbeddings,
        search_field_name_embedding: str,
        content_understanding_endpoint: str,
        document_action: DocumentAction = DocumentAction.Add,
        search_analyzer_name: str | None = None,
        use_acls: bool = False,
        enforce_access_control: bool = False,
        use_web_source: bool = False,
    ) -> None:
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.search_info = search_info
        self.embeddings = embeddings
        self.search_field_name_embedding = search_field_name_embedding
        self.content_understanding_endpoint = content_understanding_endpoint
        self.document_action = document_action
        self.search_analyzer_name = search_analyzer_name
        self.use_acls = use_acls
        self.enforce_access_control = enforce_access_control
        self.use_web_source = use_web_source

        # Same names as the custom-skill CloudIngestionStrategy, so switching modes replaces
        # the existing pipeline rather than leaving two indexers writing to the same index.
        prefix = f"{self.search_info.index_name}-cloud"
        self.skillset_name = f"{prefix}-skillset"
        self.indexer_name = f"{prefix}-indexer"
        self.data_source_name = f"{prefix}-blob"

    def build_skillset(self) -> SearchIndexerSkillset:
        content_understanding_skill = ContentUnderstandingSkill(
            name="content-understanding-skill",
            description="Extracts text, tables and page locations, and splits the content into chunks",
            context="/document",
            extraction_options=[ContentUnderstandingSkillExtractionOptions.LOCATION_METADATA],
            chunking_properties=ContentUnderstandingSkillChunkingProperties(
                unit=ContentUnderstandingSkillChunkingUnit.CHARACTERS,
                maximum_length=CHUNK_MAX_CHARACTERS,
                overlap_length=CHUNK_OVERLAP_CHARACTERS,
            ),
            inputs=[InputFieldMappingEntry(name="file_data", source="/document/file_data")],
            outputs=[OutputFieldMappingEntry(name="text_sections", target_name="text_sections")],
        )

        # Skill expressions can't concatenate a string with a number, but Text Merge can append
        # the numeric page number (wrapped in an array) to the file name.
        page_citation_skill = MergeSkill(
            name="page-citation-skill",
            description="Builds a file.pdf#page=N citation from the chunk's first page",
            context=SECTIONS_CONTEXT,
            insert_pre_tag="#page=",
            insert_post_tag="",
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/metadata_storage_name"),
                InputFieldMappingEntry(name="itemsToInsert", source=f"=[$({PAGE_NUMBER_SOURCE})]"),
            ],
            outputs=[OutputFieldMappingEntry(name="mergedText", target_name="pageCitation")],
        )

        # Only PDFs get a page fragment (matching local ingestion); other files cite the file name.
        # pageNumberFrom is 0 when Content Understanding finds no page location.
        sourcepage_skill = ConditionalSkill(
            name="sourcepage-skill",
            description="Uses the page citation for PDFs and the file name for other formats",
            context=SECTIONS_CONTEXT,
            inputs=[
                InputFieldMappingEntry(
                    name="condition",
                    source=(
                        f"=({FILE_EXTENSION_SOURCE} == '.pdf' || {FILE_EXTENSION_SOURCE} == '.PDF')"
                        f" && $({PAGE_NUMBER_SOURCE}) > 0"
                    ),
                ),
                InputFieldMappingEntry(name="whenTrue", source=f"{SECTIONS_CONTEXT}/pageCitation"),
                InputFieldMappingEntry(name="whenFalse", source="/document/metadata_storage_name"),
            ],
            outputs=[OutputFieldMappingEntry(name="output", target_name="sourcepage")],
        )

        embedding_skill = AzureOpenAIEmbeddingSkill(
            name="embedding-skill",
            description="Generates embeddings for each chunk via Azure OpenAI",
            context=SECTIONS_CONTEXT,
            resource_url=self.embeddings.azure_endpoint,
            deployment_name=self.embeddings.azure_deployment_name,
            model_name=self.embeddings.open_ai_model_name,
            dimensions=self.embeddings.open_ai_dimensions,
            inputs=[InputFieldMappingEntry(name="text", source=f"{SECTIONS_CONTEXT}/content")],
            outputs=[OutputFieldMappingEntry(name="embedding", target_name="embedding")],
        )

        mappings = [
            InputFieldMappingEntry(name="content", source=f"{SECTIONS_CONTEXT}/content"),
            InputFieldMappingEntry(name="sourcepage", source=f"{SECTIONS_CONTEXT}/sourcepage"),
            InputFieldMappingEntry(name="sourcefile", source="/document/metadata_storage_name"),
            InputFieldMappingEntry(name="storageUrl", source="/document/metadata_storage_path"),
            InputFieldMappingEntry(name=self.search_field_name_embedding, source=f"{SECTIONS_CONTEXT}/embedding"),
        ]
        if self.use_acls:
            mappings.append(InputFieldMappingEntry(name="oids", source="/document/metadata_user_ids"))
            mappings.append(InputFieldMappingEntry(name="groups", source="/document/metadata_group_ids"))
            mappings.append(
                InputFieldMappingEntry(name=METADATA_STORAGE_PATH_FIELD, source="/document/metadata_storage_path")
            )

        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.search_info.index_name,
                    parent_key_field_name="parent_id",
                    source_context=SECTIONS_CONTEXT,
                    mappings=mappings,
                )
            ],
            parameters=SearchIndexerIndexProjectionsParameters(
                projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS,
            ),
        )

        return SearchIndexerSkillset(
            name=self.skillset_name,
            description="Built-in skills: Content Understanding extraction and chunking, page citations, embeddings",
            skills=[content_understanding_skill, page_citation_skill, sourcepage_skill, embedding_skill],
            cognitive_services_account=AIServicesAccountIdentity(subdomain_url=self.content_understanding_endpoint),
            index_projection=index_projection,
        )

    def build_data_source(self) -> SearchIndexerDataSourceConnection:
        data_source = SearchIndexerDataSourceConnection(
            name=self.data_source_name,
            type=SearchIndexerDataSourceType.ADLS_GEN2 if self.use_acls else SearchIndexerDataSourceType.AZURE_BLOB,
            connection_string=self.blob_manager.get_managedidentity_connectionstring(),
            container=SearchIndexerDataContainer(name=self.blob_manager.container),
            data_deletion_detection_policy=NativeBlobSoftDeleteDeletionDetectionPolicy(),
        )
        if self.use_acls:
            # Native ADLS Gen2 permission ingestion (preview). Set after construction because the
            # SDK's connection_string overload doesn't declare this keyword.
            data_source.indexer_permission_options = [
                IndexerPermissionOption.USER_IDS,
                IndexerPermissionOption.GROUP_IDS,
            ]
        return data_source

    def build_indexer(self) -> SearchIndexer:
        return SearchIndexer(
            name=self.indexer_name,
            description="Indexer orchestrating built-in skills cloud ingestion pipeline",
            data_source_name=self.data_source_name,
            target_index_name=self.search_info.index_name,
            skillset_name=self.skillset_name,
            parameters=IndexingParameters(
                configuration=IndexingParametersConfiguration(
                    query_timeout=None,
                    data_to_extract="storageMetadata",
                    allow_skillset_to_read_file_data=True,
                )
            ),
        )

    async def setup(self) -> None:  # pragma: no cover
        logger.info("Setting up search index and built-in skillset for cloud ingestion")

        if not self.embeddings.azure_endpoint or not self.embeddings.azure_deployment_name:
            raise ValueError("Cloud ingestion requires Azure OpenAI endpoint and deployment")

        container_client = self.blob_manager.blob_service_client.get_container_client(self.blob_manager.container)
        if not await container_client.exists():
            raise ValueError(
                f"Storage container '{self.blob_manager.container}' does not exist in storage account "
                f"'{self.blob_manager.account}'. Please create the container first, or set AZURE_STORAGE_CONTAINER "
                "to an existing container name."
            )

        search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=self.search_analyzer_name,
            use_acls=self.use_acls,
            use_parent_index_projection=True,
            embeddings=self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=False,
            enforce_access_control=self.enforce_access_control,
            use_web_source=self.use_web_source,
        )
        await search_manager.create_index()
        if self.use_acls:
            await self.ensure_metadata_storage_path_field()

        async with self.search_info.create_search_indexer_client() as indexer_client:
            data_source = await indexer_client.create_or_update_data_source_connection(self.build_data_source())
            await indexer_client.create_or_update_skillset(self.build_skillset())
            await indexer_client.create_or_update_indexer(self.build_indexer())

        if self.use_acls:
            async with self.search_info.create_search_index_client() as index_client:
                index = await index_client.get_index(self.search_info.index_name)
            validate_acl_configuration(data_source, index)

    async def ensure_metadata_storage_path_field(self) -> None:  # pragma: no cover
        """ADLS Gen2 permission ingestion requires a metadata_storage_path field in the target index."""
        async with self.search_info.create_search_index_client() as index_client:
            index = await index_client.get_index(self.search_info.index_name)
            if any(field.name == METADATA_STORAGE_PATH_FIELD for field in index.fields):
                return
            logger.info("Adding %s field to index for ADLS Gen2 permission ingestion", METADATA_STORAGE_PATH_FIELD)
            index.fields.append(SimpleField(name=METADATA_STORAGE_PATH_FIELD, type="Edm.String", filterable=True))
            await index_client.create_or_update_index(index)

    async def run(self) -> None:  # pragma: no cover
        files = self.list_file_strategy.list()
        async for file in files:
            try:
                await self.blob_manager.upload_blob(file)
            finally:
                if file:
                    file.close()

        async with self.search_info.create_search_indexer_client() as indexer_client:
            previous_result = (await indexer_client.get_indexer_status(self.indexer_name)).last_result
            if previous_result is not None and previous_result.status == IndexerExecutionStatus.IN_PROGRESS:
                # Creating the indexer in setup() starts a run automatically, which may have begun
                # before the uploads above. Let it finish, then run again to pick up every file.
                logger.info("Waiting for in-progress run of indexer '%s' to finish", self.indexer_name)
                await wait_for_indexer(indexer_client, self.indexer_name, None)
                previous_result = (await indexer_client.get_indexer_status(self.indexer_name)).last_result
            previous_start_time = previous_result.start_time if previous_result else None
            await indexer_client.run_indexer(self.indexer_name)
            logger.info("Triggered indexer '%s' for cloud ingestion", self.indexer_name)
            await wait_for_indexer(indexer_client, self.indexer_name, previous_start_time)

        if self.use_acls:
            async with self.search_info.create_search_client() as search_client:
                await check_acl_ingestion(search_client, use_elevated_read=self.enforce_access_control)


def validate_acl_configuration(data_source: SearchIndexerDataSourceConnection, index: SearchIndex) -> None:
    """Fails fast if the deployed data source or index can't ingest ADLS Gen2 permissions.

    A misconfigured pipeline doesn't produce indexer errors: chunks are indexed without
    permissions, so this checks the configuration as stored by the search service.
    """
    problems = []
    if data_source.type != SearchIndexerDataSourceType.ADLS_GEN2:
        problems.append(f"data source '{data_source.name}' has type '{data_source.type}', not 'adlsgen2'")
    permission_options = set(data_source.indexer_permission_options or [])
    if not {IndexerPermissionOption.USER_IDS, IndexerPermissionOption.GROUP_IDS} <= permission_options:
        problems.append(
            f"data source '{data_source.name}' has indexerPermissionOptions {sorted(permission_options)}, "
            "expected userIds and groupIds"
        )
    fields = {field.name: field for field in index.fields}
    for field_name, permission_filter in [("oids", PermissionFilter.USER_IDS), ("groups", PermissionFilter.GROUP_IDS)]:
        field = fields.get(field_name)
        if field is None or field.permission_filter != permission_filter:
            problems.append(
                f"index field '{field_name}' is missing or doesn't have permissionFilter '{permission_filter}'"
            )
    if METADATA_STORAGE_PATH_FIELD not in fields:
        problems.append(f"index field '{METADATA_STORAGE_PATH_FIELD}' is missing")
    if problems:
        raise ValueError("ADLS Gen2 permission ingestion isn't configured correctly: " + "; ".join(problems))


async def check_acl_ingestion(search_client: SearchClient, use_elevated_read: bool) -> None:
    """Warns if indexed chunks have no permissions, which means ACL ingestion silently didn't happen.

    Files without any named user or group ACL entries are indexed with ["none"], so empty
    oids and groups fields indicate a pipeline problem rather than a file without access.
    When permission filtering is enforced, the check needs elevated read (Search Index Data
    Contributor) to see every chunk.
    """
    try:
        total_results = await search_client.search(
            search_text="*", top=0, include_total_count=True, enable_elevated_read=use_elevated_read or None
        )
        total = await total_results.get_count()
        missing_results = await search_client.search(
            search_text="*",
            filter="not oids/any() and not groups/any()",
            top=0,
            include_total_count=True,
            enable_elevated_read=use_elevated_read or None,
        )
        missing = await missing_results.get_count()
    except HttpResponseError as error:
        logger.warning("Couldn't verify that permissions were ingested: %s", error.message)
        return
    if total and missing == total:
        logger.error(
            "None of the %d indexed chunks have permissions (oids/groups). ADLS Gen2 permission ingestion didn't run; "
            "check the data source's indexerPermissionOptions and the search service's access to the storage account.",
            total,
        )
    elif missing:
        logger.warning("%d of %d indexed chunks have no permissions (oids/groups).", missing, total)
    else:
        logger.info("All %d indexed chunks have permissions.", total)


async def wait_for_indexer(
    indexer_client: SearchIndexerClient,
    indexer_name: str,
    previous_start_time: datetime | None,
    poll_interval_seconds: float = INDEXER_POLL_INTERVAL_SECONDS,
    timeout_seconds: float = INDEXER_POLL_TIMEOUT_SECONDS,
) -> None:
    """Waits for the indexer run started after ``previous_start_time`` to finish, then logs its warnings and errors.

    Warnings matter because some documents are skipped without failing the run, for example
    files larger than the search tier's extraction limit (16 MB on the Basic tier).
    """
    elapsed = 0.0
    while True:
        status = await indexer_client.get_indexer_status(indexer_name)
        result = status.last_result
        if (
            result is not None
            and result.start_time != previous_start_time
            and result.status != IndexerExecutionStatus.IN_PROGRESS
        ):
            break
        if elapsed >= timeout_seconds:
            logger.warning(
                "Indexer '%s' is still running after %d minutes. Check its status in the Azure portal.",
                indexer_name,
                timeout_seconds // 60,
            )
            return
        await asyncio.sleep(poll_interval_seconds)
        elapsed += poll_interval_seconds

    logger.info(
        "Indexer '%s' finished with status '%s': %s items processed, %s failed",
        indexer_name,
        getattr(result.status, "value", result.status),
        result.item_count,
        result.failed_item_count,
    )
    for warning in result.warnings or []:
        logger.warning("Indexer warning for '%s': %s", warning.key or warning.name, warning.message)
    for error in result.errors or []:
        logger.error("Indexer error for '%s': %s", error.key or error.name, error.error_message)
