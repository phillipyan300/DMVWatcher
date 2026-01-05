# Scripts

## run_background.sh

Start DMVWatcher in the background. The process will continue running even if you close the terminal.

**Usage:**
```bash
./scripts/run_background.sh
```

Logs are written to `dmvwatcher.log` in the project root.

## stop_background.sh

Stop the running DMVWatcher background process.

**Usage:**
```bash
./scripts/stop_background.sh
```

## com.dmvwatcher.plist

macOS Launch Agent configuration file. This allows DMVWatcher to:
- Start automatically when your Mac boots
- Automatically restart if it crashes
- Run as a system service

**⚠️ IMPORTANT:** Before installing, edit the plist file and update the hardcoded paths:
- Update `/Users/phillipyan/Documents/DMVWatcher` to your actual project path
- Update Python path if your venv is in a different location

**Installation:**
```bash
# 1. Edit paths in the plist file first!
nano scripts/com.dmvwatcher.plist

# 2. Copy to LaunchAgents
cp scripts/com.dmvwatcher.plist ~/Library/LaunchAgents/

# 3. Load and start
launchctl load ~/Library/LaunchAgents/com.dmvwatcher.plist
launchctl start com.dmvwatcher
```

**Uninstall:**
```bash
launchctl stop com.dmvwatcher
launchctl unload ~/Library/LaunchAgents/com.dmvwatcher.plist
rm ~/Library/LaunchAgents/com.dmvwatcher.plist
```

