#!/bin/sh

# Get the project root of the current script
project_root="$(cd "$(dirname $(dirname $0))" && pwd)"
app_dir="$project_root/app"

echo 'Creating Python virtual environment "app/backend/.venv"...'
python3 -m venv .venv

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
.venv/bin/python -m pip --quiet --disable-pip-version-check install -r $app_dir/backend/requirements.txt
