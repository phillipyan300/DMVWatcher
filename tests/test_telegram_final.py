#!/usr/bin/env python3
"""Final comprehensive Telegram bot test."""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def final_test():
    """Comprehensive test with all possible solutions."""
    from telegram import Bot
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print("=" * 60)
    print("TELEGRAM BOT COMPREHENSIVE TEST")
    print("=" * 60)
    
    if not bot_token:
        print("❌ Missing TELEGRAM_BOT_TOKEN")
        return False
    
    bot = Bot(token=bot_token)
    
    # Step 1: Verify bot
    print("\n[1/5] Verifying bot token...")
    try:
        bot_info = await bot.get_me()
        print(f"   ✅ Bot: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        print(f"   ❌ Invalid token: {e}")
        return False
    
    # Step 2: Check webhook
    print("\n[2/5] Checking webhook...")
    try:
        webhook = await bot.get_webhook_info()
        if webhook.url:
            print(f"   ⚠️  Webhook exists: {webhook.url}")
            print("   Deleting webhook...")
            await bot.delete_webhook(drop_pending_updates=True)
            print("   ✅ Webhook deleted")
        else:
            print("   ✅ No webhook")
    except Exception as e:
        print(f"   ⚠️  Could not check webhook: {e}")
    
    # Step 3: Get updates to find chat_id
    print("\n[3/5] Getting updates to find chat_id...")
    found_chat_id = None
    try:
        # Try to get recent updates
        updates = await bot.get_updates(limit=10)
        print(f"   Found {len(updates)} updates")
        
        if updates:
            for update in updates:
                if update.message:
                    msg_chat_id = update.message.chat.id
                    print(f"   ✅ Found chat_id from update: {msg_chat_id}")
                    found_chat_id = msg_chat_id
                    break
        else:
            print("   ⚠️  No updates found")
            print("   💡 You need to send a message to @{} first".format(bot_info.username))
    except Exception as e:
        print(f"   ⚠️  Error getting updates: {e}")
    
    # Step 4: Try sending with found chat_id
    test_chat_ids = []
    if found_chat_id:
        test_chat_ids.append(("From getUpdates", found_chat_id))
    if chat_id:
        test_chat_ids.append(("From .env", chat_id))
    
    if not test_chat_ids:
        print("\n❌ No chat_id available. Send a message to the bot first.")
        return False
    
    print(f"\n[4/5] Testing send_message with {len(test_chat_ids)} chat_id(s)...")
    for source, test_id in test_chat_ids:
        print(f"\n   Testing {source}: {test_id}")
        
        # Try integer
        try:
            result = await bot.send_message(chat_id=int(test_id), text="🧪 Test message")
            print(f"   ✅✅✅ SUCCESS with integer format!")
            print(f"   Message ID: {result.message_id}")
            print(f"   ✅✅✅ BOT IS WORKING! ✅✅✅")
            print(f"\n   Working chat_id: {test_id}")
            print(f"   Source: {source}")
            return True
        except Exception as e:
            print(f"   ❌ Integer failed: {str(e)[:80]}")
        
        # Try string
        try:
            result = await bot.send_message(chat_id=str(test_id), text="🧪 Test message")
            print(f"   ✅✅✅ SUCCESS with string format!")
            print(f"   Message ID: {result.message_id}")
            print(f"   ✅✅✅ BOT IS WORKING! ✅✅✅")
            return True
        except Exception as e:
            print(f"   ❌ String failed: {str(e)[:80]}")
    
    # Step 5: Wait for new message
    print(f"\n[5/5] Waiting for you to send a message...")
    print("   → Open Telegram")
    print("   → Message @{}".format(bot_info.username))
    print("   → Send ANY message")
    print("   → This script will detect it and reply\n")
    
    try:
        # Get current offset
        updates = await bot.get_updates()
        offset = updates[-1].update_id + 1 if updates else 0
        
        print(f"   Listening (offset: {offset})... Press Ctrl+C to cancel\n")
        
        # Poll for 30 seconds
        for attempt in range(6):  # 6 attempts * 5 seconds = 30 seconds
            try:
                updates = await bot.get_updates(offset=offset, timeout=5)
                
                for update in updates:
                    offset = update.update_id + 1
                    if update.message:
                        fresh_chat_id = update.message.chat.id
                        print(f"   📨 Got message from chat_id: {fresh_chat_id}")
                        
                        try:
                            result = await bot.send_message(
                                chat_id=fresh_chat_id,
                                text="✅ Bot works! This is a test reply."
                            )
                            print(f"   ✅✅✅ SUCCESS!")
                            print(f"   Message ID: {result.message_id}")
                            print(f"   ✅✅✅ BOT IS WORKING! ✅✅✅")
                            print(f"\n   💡 Update .env: TELEGRAM_CHAT_ID={fresh_chat_id}")
                            return True
                        except Exception as e:
                            print(f"   ❌ Failed to reply: {e}")
            except asyncio.TimeoutError:
                print(f"   ⏳ Waiting... ({attempt + 1}/6)")
                continue
        
        print("\n   ⏱️  Timeout - no message received")
    except KeyboardInterrupt:
        print("\n   ⏹️  Cancelled")
    
    print("\n" + "=" * 60)
    print("❌ ALL TESTS FAILED")
    print("=" * 60)
    print("\n📋 SUMMARY:")
    print("   Bot token: ✅ Valid")
    print("   Bot username: @{}".format(bot_info.username))
    print("   Chat ID: ❌ Cannot send messages")
    print("\n💡 REQUIRED:")
    print("   1. Open Telegram")
    print("   2. Search for @{}".format(bot_info.username))
    print("   3. Start chat")
    print("   4. Send message: 'test'")
    print("   5. Run this test again")
    
    return False

if __name__ == '__main__':
    success = asyncio.run(final_test())
    sys.exit(0 if success else 1)

