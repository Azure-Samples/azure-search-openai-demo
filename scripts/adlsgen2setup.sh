 #!/bin/sh

. ./scripts/loadenv.sh

if [ -n "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" ]; then
    echo 'AZURE_ADLS_GEN2_STORAGE_ACCOUNT must be set to continue'
    exit 1
fi

echo 'Running "adlsgen2setup.py"'

./scripts/.venv/bin/python ./scripts/adlsgen2setup.py './data/*' --data-access-control './scripts/sampleacls.json' --storage-account "$AZURE_ADLS_GEN2_STORAGE_ACCOUNT" -v
