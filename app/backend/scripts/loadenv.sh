#!/bin/bash

# Accept the index and container as arguments
index=$1
container=$2

# Enable exit on error and command echoing
set -e
set -x

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Log start of script
log_message "Starting environment setup script"

# Environment variables without quotes
log_message "Setting environment variables"
export AZURE_ENFORCE_ACCESS_CONTROL=False
export AZURE_ENV_NAME=rg-demo
export AZURE_FORMRECOGNIZER_SERVICE=cog-fr-rm72v2vn7ej6o
export AZURE_LOCATION=eastus2
export AZURE_OPENAI_CHATGPT_DEPLOYMENT=chat
export AZURE_OPENAI_CHATGPT_MODEL=gpt-35-turbo
export AZURE_OPENAI_EMB_DEPLOYMENT=embedding
export AZURE_OPENAI_EMB_MODEL_NAME=text-embedding-ada-002
export AZURE_OPENAI_GPT4V_MODEL=gpt-4
export AZURE_OPENAI_RESOURCE_GROUP=cog-rm72v2vn7ej6o
export AZURE_OPENAI_SERVICE=cog-rm72v2vn7ej6o
export AZURE_PRINCIPAL_ID=5998e964-c0a8-4fcd-af82-6e9a5110adcd
export AZURE_PRINCIPAL_ID_OTHER=8be21b40-42cc-4850-866b-6f0c717d4e66
export AZURE_RESOURCE_GROUP=rg-demo
export AZURE_SEARCH_INDEX=$index
export AZURE_SEARCH_QUERY_LANGUAGE=en-us
export AZURE_SEARCH_QUERY_SPELLER=lexicon
export AZURE_SEARCH_SEMANTIC_RANKER=free
export AZURE_SEARCH_SERVICE=gptkb-rm72v2vn7ej6o
export AZURE_STORAGE_ACCOUNT=strm72v2vn7ej6o
export AZURE_STORAGE_CONTAINER=$container
export AZURE_SUBSCRIPTION_ID=da268cd4-e89e-4d33-952a-5f61a3254e6a
export AZURE_TENANT_ID=424db043-8c7c-43c2-9241-985a4adda777
export AZURE_USE_AUTHENTICATION=False
export OPENAI_HOST=azure

log_message "Environment variables set"

# Check if antenv exists
if [ ! -d "./antenv" ]; then
    log_message "Error: antenv directory not found"
    exit 1
fi

# Check Python version in antenv
log_message "Checking Python version in antenv"
./antenv/bin/python --version || { log_message "Error: Failed to get Python version"; exit 1; }

# Check current working directory and its contents
log_message "Current working directory:"
pwd
log_message "Directory contents:"
ls -la

# Check if requirements.txt exists
if [ ! -f "scripts/requirements.txt" ]; then
    log_message "Error: scripts/requirements.txt not found"
    exit 1
fi

log_message "Installing dependencies from requirements.txt into antenv"
./antenv/bin/python -m pip install -r scripts/requirements.txt || { log_message "Error: Failed to install requirements"; exit 1; }

log_message "Installed packages in antenv:"
./antenv/bin/pip list

log_message "Script completed successfully"