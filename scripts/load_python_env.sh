 #!/bin/sh

echo 'Creating Python virtual environment "scripts/.venv"...'
python3 -m venv scripts/.venv

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
./scripts/.venv/bin/python -m pip --quiet --disable-pip-version-check install -r scripts/requirements.txt
