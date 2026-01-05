# DMVWatcher

Monitor DMV appointment availability and get instant Telegram notifications when appointments open up.

## Features

- 🎯 Monitor multiple locations simultaneously
- 📅 Filter appointments by maximum date
- 📱 Telegram notifications when appointments become available
- ⏰ Configurable polling intervals
- 🚫 Anti-spam: Sends one notification, then waits 1 hour
- 🔄 Runs continuously in the background
- 📊 Detailed logging

## Quick Start

### 1. Installation

```bash
# Clone or download this repository
cd DMVWatcher

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Telegram Bot

#### Step 1: Create Bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. **Save the bot token** (looks like: `1234567890:ABCdef...`)

#### Step 2: Get Your Chat ID
**You must send a message to your bot first!**

1. Search for your bot by username (e.g., `@your_bot_name_bot`)
2. Start a chat and send any message (e.g., "Hello")
3. Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
4. Look for `"chat":{"id":123456789}` - that number is your chat ID

**Alternative:** Use **@RawDataBot** - it will show your user ID directly.

### 3. Create Configuration

Copy `config.example.json` to `config.json`:

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "targets": ["Mercer"],
  "monitoring_duration_minutes": 120,
  "polling_interval_seconds": 300,
  "max_date": "01/18/2026",
  "url": "https://telegov.njportal.com/njmvcmobileunit/AppointmentWizard/265",
  "telegram": {
    "bot_token": "your_bot_token_here",
    "chat_id": "your_chat_id_here"
  }
}
```

**Or use environment variables** (recommended for sensitive data):

Create `.env` file:
```bash
TELEGRAM_BOT_TOKEN='your_bot_token_here'
TELEGRAM_CHAT_ID='your_chat_id_here'
```

Environment variables take priority over `config.json` for Telegram credentials.

### 4. Run

```bash
# Foreground (for testing)
python dmvwatcher.py --config config.json

# Background (recommended)
./scripts/run_background.sh
```

## Configuration

### Config File Options

| Option | Description | Default |
|--------|-------------|---------|
| `targets` | Array of county names to monitor (e.g., `["Mercer", "Camden"]`) | Required |
| `monitoring_duration_minutes` | How long to monitor (0 = indefinite) | `0` |
| `polling_interval_seconds` | Seconds between checks | `300` (5 minutes) |
| `max_date` | Only alert if appointment is before this date (MM/DD/YYYY) | None |
| `url` | DMV appointment page URL | Default NJ URL |
| `telegram.bot_token` | Your Telegram bot token | Required |
| `telegram.chat_id` | Your Telegram chat ID | Required |

### Command-Line Options

```bash
python dmvwatcher.py [OPTIONS]

Options:
  --targets, -t        County names to monitor (comma-separated)
  --duration, -d       Monitoring duration in minutes (0 = indefinite)
  --interval, -i       Polling interval in seconds
  --max-date           Maximum appointment date (MM/DD/YYYY)
  --config, -c         Path to config file
  --url                DMV appointment page URL
```

**Examples:**
```bash
# Using config file
python dmvwatcher.py --config config.json

# Using command-line arguments
python dmvwatcher.py --targets Mercer,Camden --duration 120 --interval 300

# Mix both (CLI overrides config file)
python dmvwatcher.py --config config.json --interval 600
```

## Running in Background

### Option 1: Helper Scripts (Recommended)

```bash
# Start
./scripts/run_background.sh

# Stop
./scripts/stop_background.sh

# View logs
tail -f dmvwatcher.log
```

### Option 2: macOS Launch Agent (Auto-start on boot)

```bash
# Install (runs on boot, auto-restarts if crashes)
cp scripts/com.dmvwatcher.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dmvwatcher.plist
launchctl start com.dmvwatcher

# Stop
launchctl stop com.dmvwatcher

# Uninstall
launchctl unload ~/Library/LaunchAgents/com.dmvwatcher.plist
rm ~/Library/LaunchAgents/com.dmvwatcher.plist
```

### Option 3: Manual Background

```bash
# Start
nohup python dmvwatcher.py --config config.json > dmvwatcher.log 2>&1 &

# Stop (find PID first)
ps aux | grep dmvwatcher.py
kill <PID>
```

### Option 4: Screen/Tmux (For SSH sessions)

```bash
# Using screen
screen -S dmvwatcher
python dmvwatcher.py --config config.json
# Press Ctrl+A then D to detach

# Reattach later
screen -r dmvwatcher
```

## How It Works

1. **Monitors** specified DMV locations (by county name)
2. **Checks** every N seconds (configurable) for appointment availability
3. **Detects** when "Make Appointment" button appears (source of truth)
4. **Filters** by date if `max_date` is set
5. **Sends** ONE Telegram notification when appointment found
6. **Waits** 1 hour after notification to avoid spam
7. **Continues** monitoring after the wait period

## Output & Logging

- **Console**: Real-time status updates
- **Log file**: `dmvwatcher.log` (detailed logging, auto-rotated)
- **Status file**: `status.json` (last known status, not committed to git)
- **Telegram**: Instant notifications when appointments available

## Project Structure

```
DMVWatcher/
├── dmvwatcher.py          # Main entry point
├── config.example.json     # Example configuration
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── src/                   # Source code
│   ├── config.py         # Configuration loading
│   ├── notifications.py  # Telegram notifications
│   └── watcher.py        # Core monitoring logic
├── scripts/               # Helper scripts
│   ├── run_background.sh # Start in background
│   ├── stop_background.sh # Stop background process
│   └── com.dmvwatcher.plist # macOS Launch Agent
└── tests/                 # Test files
    └── test_telegram_final.py # Telegram bot test
```

## Troubleshooting

### Telegram Issues

**"Chat not found" error:**
- Make sure you sent at least one message to your bot first
- Double-check chat_id is correct (your user ID)
- Try running `python tests/test_telegram_final.py` to test

**"Unauthorized" error:**
- Check bot token is correct (no extra spaces or quotes)
- Verify bot was created successfully via BotFather

**Bot not sending messages:**
- Ensure you sent a message to the bot first (required by Telegram)
- Check `.env` file has correct values (or `config.json`)
- Verify bot is not blocked

### Monitoring Issues

**No appointments detected:**
- Check `targets` match county names exactly (case-insensitive)
- Verify URL is correct
- Check logs: `tail -f dmvwatcher.log`
- Ensure "Make Appointment" button exists on the page

**Script stops running:**
- Check logs for errors
- Verify internet connection
- Check if Playwright browser crashed (restart script)

**False positives:**
- The script uses "Make Appointment" button as source of truth
- If button exists, appointment is available
- Check logs to see what was detected

## Testing

Test your Telegram bot setup:

```bash
python tests/test_telegram_final.py
```

This will verify your bot token and chat_id are correct.

## Requirements

- Python 3.8+
- Playwright (Chromium browser)
- Telegram bot token and chat ID
- Internet connection

## License

Personal use project - modify as needed.

## Notes

- Logs and status files are not committed to git (see `.gitignore`)
- `.env` file should never be committed (contains sensitive tokens)
- The script creates a fresh browser session for each check to avoid caching issues
- Anti-spam logic: After sending a notification, waits 1 hour before checking again
