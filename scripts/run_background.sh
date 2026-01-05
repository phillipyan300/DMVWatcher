#!/bin/bash
# Run DMVWatcher in the background

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

# Run in background with nohup (survives terminal close)
nohup python dmvwatcher.py $CONFIG_ARG > dmvwatcher.log 2>&1 &

echo "DMVWatcher started in background (PID: $!)"
echo "Config: ${CONFIG_ARG:-'default/CLI args'}"
echo "Logs: tail -f dmvwatcher.log"
echo "Stop: ./scripts/stop_background.sh"

