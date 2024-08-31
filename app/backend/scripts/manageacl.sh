 #!/bin/sh

. ./scripts/loadenv.sh

echo "Running manageacl.py. Arguments to script: $@"
  ./antenv/bin/python ./scripts/manageacl.py --search-service "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX" $@