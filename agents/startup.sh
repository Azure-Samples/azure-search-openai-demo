#!/bin/bash
# Startup script for Azure App Service
# Install packages if not already installed, then start the server

set -e  # Exit on error

echo "=== Agents Service Startup Script ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Change to the correct directory
cd /home/site/wwwroot || cd "$(dirname "$0")/.." || pwd

echo "Working directory: $(pwd)"
echo "Files in directory:"
ls -la

# Install hypercorn if not available
if ! command -v hypercorn &> /dev/null && ! python -c "import hypercorn" 2>/dev/null; then
    echo "Hypercorn not found. Installing hypercorn..."
    pip install --no-cache-dir hypercorn
    echo "Hypercorn installed"
else
    echo "Hypercorn is available"
fi

# Verify hypercorn is installed
if ! python -c "import hypercorn" 2>/dev/null; then
    echo "ERROR: Failed to import hypercorn"
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found in $(pwd)"
    echo "Looking for main.py..."
    find . -name "main.py" -type f 2>/dev/null || echo "main.py not found anywhere"
    exit 1
fi

echo "Starting hypercorn server..."
# Ensure we're in the right directory and Python can find the module
cd /home/site/wwwroot
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
# Use python -m hypercorn to ensure we use the installed package
exec python -m hypercorn main:app --bind 0.0.0.0:8000 --log-level info
