#!/bin/sh

USE_CLOUD_INGESTION=$(azd env get-value USE_CLOUD_INGESTION)
if [ "$USE_CLOUD_INGESTION" != "true" ]; then
  exit 0
fi

. ./scripts/load_python_env.sh

./.venv/bin/python ./app/backend/setup_cloud_ingestion.py
