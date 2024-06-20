port=50505
host=localhost
../../.venv/bin/python -m quart --app main:app run --port "$port" --host "$host" --reload
if [ $? -ne 0 ]; then
    echo "Failed to start backend"
    exit $?
fi