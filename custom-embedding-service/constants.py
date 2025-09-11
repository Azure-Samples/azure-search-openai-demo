import os

# API Authentication
API_KEY = os.getenv("PATENTSBERTA_API_KEY")

# Request Limits and Validation Constants
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "120"))  # Maximum number of texts per request
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "20000"))  # Maximum characters per text
MIN_TEXT_LENGTH = 1  # Minimum characters per text
MAX_TOTAL_CHARS = int(os.getenv("MAX_TOTAL_CHARS", "100000"))  # Maximum total characters in request

# Model Configuration
MODEL_NAME = "AI-Growth-Lab/PatentSBERTa"
MODEL_MAX_LENGTH = 512
EMBEDDING_DIMENSIONS = 768
MODEL_DESCRIPTION = "Patent-specific BERT model for technical document embeddings"