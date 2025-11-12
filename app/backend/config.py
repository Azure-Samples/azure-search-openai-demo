CONFIG_OPENAI_TOKEN = "openai_token"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_ASK_APPROACH = "ask_approach"
CONFIG_CHAT_APPROACH = "chat_approach"
CONFIG_GLOBAL_BLOB_MANAGER = "global_blob_manager"
CONFIG_USER_BLOB_MANAGER = "user_blob_manager"
CONFIG_USER_UPLOAD_ENABLED = "user_upload_enabled"
CONFIG_AUTH_CLIENT = "auth_client"
CONFIG_SEMANTIC_RANKER_DEPLOYED = "semantic_ranker_deployed"
CONFIG_QUERY_REWRITING_ENABLED = "query_rewriting_enabled"
CONFIG_REASONING_EFFORT_ENABLED = "reasoning_effort_enabled"
CONFIG_DEFAULT_REASONING_EFFORT = "default_reasoning_effort"
CONFIG_VECTOR_SEARCH_ENABLED = "vector_search_enabled"
CONFIG_SEARCH_CLIENT = "search_client"
CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_AGENT_CLIENT = "agent_client"
CONFIG_INGESTER = "ingester"
CONFIG_LANGUAGE_PICKER_ENABLED = "language_picker_enabled"
CONFIG_SPEECH_INPUT_ENABLED = "speech_input_enabled"
CONFIG_SPEECH_OUTPUT_BROWSER_ENABLED = "speech_output_browser_enabled"
CONFIG_SPEECH_OUTPUT_AZURE_ENABLED = "speech_output_azure_enabled"
CONFIG_SPEECH_SERVICE_ID = "speech_service_id"
CONFIG_SPEECH_SERVICE_LOCATION = "speech_service_location"
CONFIG_SPEECH_SERVICE_TOKEN = "speech_service_token"
CONFIG_SPEECH_SERVICE_VOICE = "speech_service_voice"
CONFIG_STREAMING_ENABLED = "streaming_enabled"
CONFIG_CHAT_HISTORY_BROWSER_ENABLED = "chat_history_browser_enabled"
CONFIG_CHAT_HISTORY_COSMOS_ENABLED = "chat_history_cosmos_enabled"
CONFIG_AGENTIC_RETRIEVAL_ENABLED = "agentic_retrieval"
CONFIG_COSMOS_HISTORY_CLIENT = "cosmos_history_client"
CONFIG_COSMOS_HISTORY_CONTAINER = "cosmos_history_container"
CONFIG_COSMOS_HISTORY_VERSION = "cosmos_history_version"
CONFIG_MULTIMODAL_ENABLED = "multimodal_enabled"
CONFIG_RAG_SEARCH_TEXT_EMBEDDINGS = "rag_search_text_embeddings"
CONFIG_RAG_SEARCH_IMAGE_EMBEDDINGS = "rag_search_image_embeddings"
CONFIG_RAG_SEND_TEXT_SOURCES = "rag_send_text_sources"
CONFIG_RAG_SEND_IMAGE_SOURCES = "rag_send_image_sources"
CONFIG_CACHE = "cache"

# Feature flags and provider keys (Phase 1B scaffolding)
import os

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
WEB_CACHE_TTL_S = int(os.getenv("WEB_CACHE_TTL_S", "3600"))
REDIS_URL = os.getenv("REDIS_URL")  # Optional Redis cache URL

# OCR Configuration
OCR_PROVIDER = os.getenv("OCR_PROVIDER", "none").lower()  # deepseek, azure_document_intelligence, none
OCR_ON_INGEST = os.getenv("OCR_ON_INGEST", "false").lower() == "true"  # Run OCR during document ingestion
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_OCR_MODEL = os.getenv("DEEPSEEK_OCR_MODEL", "deepseek-ocr")
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
AZURE_DOCUMENT_INTELLIGENCE_MODEL = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-read")

# NOMIC Embeddings Configuration
NOMIC_API_KEY = os.getenv("NOMIC_API_KEY")
NOMIC_ENDPOINT = os.getenv("NOMIC_ENDPOINT")  # Optional custom endpoint
NOMIC_USE_SDK = os.getenv("NOMIC_USE_SDK", "false").lower() == "true"  # Use Python SDK instead of API
NOMIC_INFERENCE_MODE = os.getenv("NOMIC_INFERENCE_MODE", "remote").lower()  # local or remote (SDK only)
ENABLE_NOMIC_EMBEDDINGS = os.getenv("ENABLE_NOMIC_EMBEDDINGS", "false").lower() == "true"