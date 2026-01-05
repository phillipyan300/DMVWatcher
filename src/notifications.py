"""Notification handling - Telegram bot."""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """Handle notifications via Telegram bot."""
    
    def __init__(self, telegram_config: Optional[Dict] = None):
        """
        Initialize notification service.
        
        Args:
            telegram_config: Dict with Telegram credentials {'bot_token', 'chat_id'}
        """
        self.bot = None
        self.chat_id = None
        
        logger.debug(f"NotificationService init: telegram_config={'provided' if telegram_config else 'None'}")
        if telegram_config:
            logger.debug(f"Telegram config keys: {list(telegram_config.keys())}")
            self._setup_telegram(telegram_config)
        else:
            logger.warning("No telegram_config provided to NotificationService")
    
    def _setup_telegram(self, telegram_config: Dict):
        """Setup Telegram bot."""
        try:
            from telegram import Bot
            bot_token = telegram_config.get('bot_token')
            self.chat_id = telegram_config.get('chat_id')
            
            logger.debug(f"Setting up Telegram: bot_token={'SET' if bot_token else 'MISSING'}, chat_id={self.chat_id if self.chat_id else 'MISSING'}")
            
            if bot_token and self.chat_id:
                self.bot = Bot(token=bot_token)
                logger.info(f"Telegram notifications enabled (chat_id: {self.chat_id})")
                # Test if bot can access chat (user must have sent a message to bot first)
                self._test_bot_connection()
            else:
                logger.warning(f"Telegram config incomplete - bot_token={'SET' if bot_token else 'MISSING'}, chat_id={'SET' if self.chat_id else 'MISSING'}")
                self.bot = None
        except ImportError:
            logger.warning("python-telegram-bot library not installed. Install with: pip install python-telegram-bot")
        except Exception as e:
            logger.warning(f"Failed to initialize Telegram bot: {e}. Notifications disabled.")
    
    def _test_bot_connection(self):
        """Test if bot can access the chat (user must have initiated conversation)."""
        try:
            import asyncio
            chat_id = int(self.chat_id) if isinstance(self.chat_id, str) else self.chat_id
            
            async def _test():
                try:
                    # Try chat_id as string first
                    test_chat_id = str(chat_id)
                    chat = await self.bot.get_chat(chat_id=test_chat_id)
                    logger.debug(f"Bot connection test successful - chat: {chat.title if hasattr(chat, 'title') else 'Private chat'}")
                    return True
                except Exception as e1:
                    # Try as integer if string failed
                    try:
                        test_chat_id = int(chat_id)
                        chat = await self.bot.get_chat(chat_id=test_chat_id)
                        logger.debug(f"Bot connection test successful (with int chat_id) - chat: {chat.title if hasattr(chat, 'title') else 'Private chat'}")
                        return True
                    except Exception as e2:
                        error_msg = str(e1) + " / " + str(e2)
                        if "Chat not found" in error_msg or "chat not found" in error_msg.lower():
                            logger.warning("⚠️  Bot cannot access chat.")
                            logger.warning("   Possible causes:")
                            logger.warning("   1. User must send a FRESH message to the bot RIGHT NOW")
                            logger.warning("   2. User has blocked the bot")
                            logger.warning("   3. User privacy settings prevent bot messages")
                            logger.warning("   4. Chat ID format issue")
                            logger.warning(f"   Trying chat_id as: string='{str(chat_id)}', int={int(chat_id) if str(chat_id).isdigit() else 'N/A'}")
                            return False
                        raise
            
            # Run test synchronously
            result = asyncio.run(_test())
            if not result:
                logger.warning("Telegram bot initialized but cannot send messages until user starts conversation")
        except Exception as e:
            logger.debug(f"Bot connection test failed: {e}")
    
    def send_message(self, message: str) -> bool:
        """Send message via Telegram bot if configured."""
        if not self.bot or not self.chat_id:
            return False
        
        try:
            import asyncio
            from telegram import Bot
            
            # Telegram supports up to 4096 characters per message
            if len(message) > 4000:
                message = message[:3997] + "..."
            
            # Clean chat_id
            chat_id_str = str(self.chat_id).strip() if self.chat_id else None
            if not chat_id_str:
                logger.error("chat_id is empty")
                return False
            
            chat_id_int = int(chat_id_str) if chat_id_str.isdigit() else None
            
            # Create a fresh Bot instance for each send to avoid event loop issues
            # Get token from existing bot
            bot_token = self.bot.token
            
            # python-telegram-bot v20+ uses async API - need to await the coroutine
            async def _send():
                # Create fresh bot instance
                bot = Bot(token=bot_token)
                # Try integer format first (most common)
                if chat_id_int is not None:
                    try:
                        result = await bot.send_message(chat_id=chat_id_int, text=message)
                        return result
                    except Exception as e1:
                        error_str = str(e1)
                        # If integer fails with "chat not found", try string
                        if "chat not found" in error_str.lower():
                            logger.debug(f"Integer format failed, trying string format")
                            try:
                                result = await bot.send_message(chat_id=chat_id_str, text=message)
                                return result
                            except Exception as e2:
                                logger.error(f"Both formats failed - int: {e1}, str: {e2}")
                                raise e1
                        else:
                            raise
                else:
                    # Try string format
                    result = await bot.send_message(chat_id=chat_id_str, text=message)
                    return result
            
            # Run the async function - asyncio.run() creates a fresh event loop
            asyncio.run(_send())
            logger.info("📱 Telegram message sent successfully")
            return True
        except RuntimeError as e:
            # Handle event loop issues
            if "asyncio.run() cannot be called" in str(e) or "Event loop is running" in str(e):
                # If there's already an event loop, use a different approach
                import asyncio
                from telegram import Bot
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        logger.error("Cannot use asyncio.run() when event loop is already running")
                        return False
                    # Create fresh bot instance (same as main path)
                    bot_token = self.bot.token
                    bot = Bot(token=bot_token)
                    # Try integer first, then string
                    try:
                        if chat_id_int is not None:
                            loop.run_until_complete(bot.send_message(chat_id=chat_id_int, text=message))
                        else:
                            loop.run_until_complete(bot.send_message(chat_id=chat_id_str, text=message))
                    except Exception as e1:
                        # Try other format if first fails
                        if chat_id_int is not None:
                            loop.run_until_complete(bot.send_message(chat_id=chat_id_str, text=message))
                        else:
                            raise e1
                    logger.info("📱 Telegram message sent successfully")
                    return True
                except Exception as inner_e:
                    logger.error(f"Failed to send via existing event loop: {inner_e}")
                    return False
            raise
        except Exception as e:
            error_msg = str(e)
            if "Chat not found" in error_msg or "chat not found" in error_msg.lower():
                logger.error(f"Failed to send Telegram message: Chat not found.")
                logger.error(f"Your chat_id is: {self.chat_id}")
                logger.error("Possible causes:")
                logger.error("1. The bot hasn't been started by the user (send /start to your bot)")
                logger.error("2. The chat_id is incorrect")
                logger.error("3. The user has blocked the bot")
                logger.error("To verify your chat_id:")
                logger.error(f"   Visit: https://api.telegram.org/bot{self.bot.token}/getUpdates")
                logger.error("   Look for 'chat':{'id':123456789} in the response")
            else:
                logger.error(f"Failed to send Telegram message: {e}")
                logger.error(f"Error type: {type(e).__name__}")
            return False
    
    def format_notification(self, county: str, location_info: Dict, url: str, appt_info: Dict) -> str:
        """Format notification message for available appointments."""
        message = f"""🚨 APPOINTMENT AVAILABLE! 🚨

Location: {location_info['name']}
County: {county}
Appointments Available: {appt_info['count'] or 'Unknown'}
Next Available: {appt_info['next_available'] or 'Unknown'}

Book now: {url}
"""
        return message
    
    def notify_availability(self, county: str, location_info: Dict, url: str, appt_info: Dict):
        """Send notification when appointments become available."""
        notification = self.format_notification(county, location_info, url, appt_info)
        logger.info(notification)
        
        # Send Telegram message if bot is configured
        if self.bot:
            self.send_message(notification)
        else:
            logger.info("Telegram bot not configured - notification only logged to console/file")
