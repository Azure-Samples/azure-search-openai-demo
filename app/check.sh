#!/bin/bash

echo "=== Checking for Missing Imports ==="

# Check if prepdocs module is correctly imported
echo -e "\n--- Checking prepdocs imports ---"
grep -n "from prepdocs import" /workspaces/azure-search-openai-demo/app/backend/app.py

# Check if the domain classifier and orchestrator files exist
echo -e "\n--- Checking for approach files ---"
ls -la /workspaces/azure-search-openai-demo/app/backend/approaches/domain_classifier.py 2>/dev/null || echo "❌ domain_classifier.py not found"
ls -la /workspaces/azure-search-openai-demo/app/backend/approaches/orchestrator_approach.py 2>/dev/null || echo "❌ orchestrator_approach.py not found"

# Check Python path
echo -e "\n--- Python Path ---"
cd /workspaces/azure-search-openai-demo/app/backend
python3 -c "import sys; print('\n'.join(sys.path))"

echo -e "\n=== Check Complete ==="