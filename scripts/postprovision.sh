 #!/bin/sh

if ! command -v python -v &> /dev/null
then
    echo 'Python not found on $PATH'
    exit -1
fi

echo 'Creating python virtual environment "scripts/.venv"'
python -m venv scripts/.venv


echo 'Installing dependencies from "requirements.txt" into virtual environment'
./scripts/.venv/bin/python -m pip install -r scripts/requirements.txt

if [ "$AZURE_STORATE_ACCOUNT" == "" ]
then
    echo 'Environment variables not set - this script assumes that it runs as part of an azd postprovision hook.'
    echo 'You can run the script manually by passing in the appropriate command line parameters after'
    echo 'activting the scripts/.venv virtual environment.'
    echo 'For more information about virtual environments, see https://docs.python.org/3/tutorial/venv.html'
    echo
    exit -1
fi

echo 'Running "prepdocs.py"'
./scripts/.venv/bin/python scripts/prepdocs.py 'data/*' --storageaccount "$AZURE_STORAGE_ACCOUNT" --container "$AZURE_STORAGE_CONTAINER" --searchservice "$AZURE_SEARCH_SERVICE" --index "$AZURE_SEARCH_INDEX"

echo "Done - if you want to run prepdocs again, please activate the scripts/.venv python virtual environment first".
echo 'For more information about virtual environments, see https://docs.python.org/3/tutorial/venv.html'
