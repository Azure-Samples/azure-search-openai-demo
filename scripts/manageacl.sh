 #!/bin/sh

. ./scripts/loadenv.sh

echo "Running manageacl.py. Arguments to script: $@"
  ./.venv/bin/python ./scripts/manageacl.py --search-service "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" $@
