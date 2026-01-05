#!/usr/bin/env python3
"""
DMVWatcher - Monitor DMV appointment availability
Monitors specified locations and alerts when appointments become available.
"""

import argparse
import logging
import sys

# Load .env file if it exists (must be before other imports that use env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading

from src.config import load_config_file, load_telegram_config
from src.notifications import NotificationService
from src.watcher import DMVWatcher


# Configure logging
def setup_logging(log_file: str = "dmvwatcher.log"):
    """Set up logging to both file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Monitor DMV appointment availability',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use config file
  python dmvwatcher.py --config config.json
  
  # Command line only
  python dmvwatcher.py --targets Mercer Camden --duration 120 --interval 300
  
  # Monitor indefinitely
  python dmvwatcher.py --targets Mercer --duration 0
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to config file (JSON)'
    )
    parser.add_argument(
        '--targets', '-t',
        nargs='+',
        help='County names to monitor (e.g., Mercer Camden Atlantic)'
    )
    parser.add_argument(
        '--duration', '-d',
        type=int,
        help='Monitoring duration in minutes (0 or omit for indefinite)'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        help='Polling interval in seconds (default: 300)'
    )
    parser.add_argument(
        '--url',
        type=str,
        help='Appointment booking page URL'
    )
    parser.add_argument(
        '--max-date',
        type=str,
        help='Maximum date for appointments (MM/DD/YYYY format, e.g., 01/18/2026). Only alert if next available is before this date.'
    )
    
    args = parser.parse_args()
    
    # Load config file if provided
    config = {}
    if args.config:
        try:
            config = load_config_file(args.config)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
    
    # Merge config with command-line args (CLI takes precedence)
    targets = args.targets or config.get('targets', [])
    duration = args.duration if args.duration is not None else config.get('monitoring_duration_minutes')
    interval = args.interval or config.get('polling_interval_seconds', 300)
    url = args.url or config.get('url', 'https://telegov.njportal.com/njmvcmobileunit/AppointmentWizard/265')
    max_date = args.max_date or config.get('max_date')
    
    # Load Telegram config (from config file or environment variables)
    telegram_config = load_telegram_config(config)
    
    # Debug: Log Telegram config status
    if telegram_config:
        logger.info(f"Telegram config loaded: bot_token={'***' + telegram_config.get('bot_token', '')[-4:] if telegram_config.get('bot_token') else 'MISSING'}, chat_id={telegram_config.get('chat_id', 'MISSING')}")
    else:
        logger.warning("No Telegram config found. Check .env file or config.json")
        logger.info("To use Telegram: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
        logger.info("Or add 'telegram' section to config.json")
    
    # Validate
    if not targets:
        logger.error("No targets specified. Use --targets or config file.")
        sys.exit(1)
    
    # Create notification service
    notification_service = NotificationService(telegram_config=telegram_config)
    
    # Create watcher and start monitoring
    watcher = DMVWatcher(
        targets=targets, 
        url=url, 
        polling_interval=interval, 
        max_date=max_date,
        notification_service=notification_service
    )
    watcher.monitor(duration_minutes=duration if duration != 0 else None)


if __name__ == '__main__':
    main()
