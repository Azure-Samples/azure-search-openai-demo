#!/bin/sh

# cd into the parent directory of the script, 
# so that the script generates virtual environments always in the same path.
cd "${0%/*}" || exit 1

cd ../
echo 'Creating python virtual environment ".venv"'
python3 -m venv .venv

echo ""
echo "Restoring backend python packages"
echo ""

./.venv/bin/python -m pip install -r app/backend/requirements.txt
out=$?
if [ $out -ne 0 ]; then
    echo "Failed to restore backend python packages"
    exit $out
fi

echo ""
echo "Restoring frontend npm packages"
echo ""

cd app/frontend
npm install
out=$?
if [ $out -ne 0 ]; then
    echo "Failed to restore frontend npm packages"
    exit $out
fi

echo ""
echo "Building frontend"
echo ""

npm run build
out=$?
if [ $out -ne 0 ]; then
    echo "Failed to build frontend"
    exit $out
fi

echo ""
echo "Starting backend"
echo ""

cd ../backend

port=50505
host=localhost
../../.venv/bin/python -m quart --app main:app run --port "$port" --host "$host" --reload
out=$?
if [ $out -ne 0 ]; then
    echo "Failed to start backend"
    exit $out
fi
