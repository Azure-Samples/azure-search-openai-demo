 #!/bin/sh

. ./scripts/loadenv.sh

echo 'Running "auth_update.py"'
./.venv/bin/python ./scripts/auth_update.py --appid "$AUTH_APP_ID" --uri "$BACKEND_URI"
