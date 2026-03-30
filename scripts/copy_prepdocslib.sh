#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v python3 > /dev/null 2>&1; then
    PYTHON=python3
elif command -v python > /dev/null 2>&1; then
    PYTHON=python
else
    echo "Python not found, please install python3." >&2
    exit 1
fi

$PYTHON "$DIR/copy_prepdocslib.py"
