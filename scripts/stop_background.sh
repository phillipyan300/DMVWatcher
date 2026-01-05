#!/bin/bash
# Stop DMVWatcher background process

PID=$(ps aux | grep "[d]mvwatcher.py" | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "DMVWatcher is not running"
else
    kill $PID
    echo "DMVWatcher stopped (PID: $PID)"
fi

