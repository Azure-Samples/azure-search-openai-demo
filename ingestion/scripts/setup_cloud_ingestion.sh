#!/bin/bash

echo "Setting up cloud ingestion..."

# Load environment variables from azd
eval "$(azd env get-values)"

# Run the cloud ingestion setup script
python3 "$(dirname "$0")/setup_cloud_ingestion.py"

echo "Cloud ingestion setup complete."
