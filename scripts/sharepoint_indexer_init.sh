#!/bin/sh

USE_CLOUD_INGESTION_SHAREPOINT=$(azd env get-value USE_CLOUD_INGESTION_SHAREPOINT 2>/dev/null)
if [ "$USE_CLOUD_INGESTION_SHAREPOINT" != "true" ]; then
  echo "USE_CLOUD_INGESTION_SHAREPOINT is not set, skipping SharePoint indexer app setup."
  exit 0
fi

. ./scripts/load_python_env.sh

./.venv/bin/python ./scripts/sharepoint_indexer_init.py
