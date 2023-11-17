 #!/bin/sh

. ./evaluation/loadenv.sh

echo 'Running "evaluate.py"'
./evaluation/.venv/bin/python ./evaluation/evaluate.py
