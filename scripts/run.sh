#!/bin/bash
# Run DMVWatcher (foreground - easier for debugging)

# Get the project root directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"
source venv/bin/activate

# Check if config file exists, use it if available
CONFIG_ARG=""
if [ -f "config.json" ]; then
    CONFIG_ARG="--config config.json"
fi

# Run in foreground (easier debugging, can see output directly)
python dmvwatcher.py $CONFIG_ARG

