"""Configuration loading and management."""

import json
import logging
import os
from typing import Dict, Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file into environment variables
except ImportError:
    logging.getLogger(__name__).warning("python-dotenv not installed. .env file will not be loaded. Install with: pip install python-dotenv")
except Exception as e:
    logging.getLogger(__name__).warning(f"Failed to load .env file: {e}")


def load_config_file(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Error loading config file: {e}")


def load_telegram_from_env() -> Optional[Dict]:
    """Load Telegram credentials from environment variables."""
    logger = logging.getLogger(__name__)
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    # Strip whitespace from values
    if bot_token:
        bot_token = bot_token.strip()
    if chat_id:
        chat_id = chat_id.strip()
    
    logger.debug(f"Loading Telegram from env: bot_token={'SET' if bot_token else 'NOT SET'}, chat_id={chat_id if chat_id else 'NOT SET'}")
    
    if bot_token and chat_id:
        return {
            'bot_token': bot_token,
            'chat_id': chat_id
        }
    return None


def load_telegram_config(config: Dict) -> Optional[Dict]:
    """
    Load Telegram configuration from config dict or environment variables.
    
    Args:
        config: Configuration dictionary (from JSON file)
        
    Returns:
        Telegram config dict or None if not configured
    """
    logger = logging.getLogger(__name__)
    
    # First try environment variables (highest priority - real credentials)
    env_config = load_telegram_from_env()
    if env_config:
        logger.debug("Telegram config found in environment variables")
        return env_config
    
    # Fall back to config file (may have placeholder values)
    if config.get('telegram'):
        telegram_config = config['telegram']
        # Check if config file has placeholder/example values
        bot_token = telegram_config.get('bot_token', '')
        if bot_token and bot_token not in ['your_bot_token_here', '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz']:
            logger.debug("Telegram config found in config file")
            return telegram_config
        else:
            logger.warning("Config file has placeholder Telegram values - ignoring")
    
    return None
