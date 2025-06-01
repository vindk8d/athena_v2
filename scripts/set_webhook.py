#!/usr/bin/env python3
"""
Script to set and verify Telegram webhook for Athena bot.
"""

import os
import requests
import sys
from urllib.parse import urljoin

def get_bot_token():
    """Get bot token from environment."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)
    return token

def get_webhook_url():
    """Get webhook URL from environment."""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("Error: WEBHOOK_URL environment variable not set")
        print("Set it to: https://your-app-name.onrender.com/webhook/telegram")
        sys.exit(1)
    return webhook_url

def set_webhook(bot_token, webhook_url, secret_token=None):
    """Set the webhook for the bot."""
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    data = {
        "url": webhook_url,
        "drop_pending_updates": True  # Clear any pending updates
    }
    
    if secret_token:
        data["secret_token"] = secret_token
    
    response = requests.post(api_url, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print(f"✅ Webhook set successfully to: {webhook_url}")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description')}")
            return False
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")
        return False

def get_webhook_info(bot_token):
    """Get current webhook information."""
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    response = requests.get(api_url)
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            webhook_info = result.get("result", {})
            print("\n📋 Current Webhook Info:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"   Pending update count: {webhook_info.get('pending_update_count', 0)}")
            print(f"   Last error date: {webhook_info.get('last_error_date', 'None')}")
            print(f"   Last error message: {webhook_info.get('last_error_message', 'None')}")
            print(f"   Max connections: {webhook_info.get('max_connections', 'Default')}")
            return webhook_info
        else:
            print(f"❌ Failed to get webhook info: {result.get('description')}")
            return None
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")
        return None

def delete_webhook(bot_token):
    """Delete the current webhook."""
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    response = requests.post(api_url, data={"drop_pending_updates": True})
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("✅ Webhook deleted successfully")
            return True
        else:
            print(f"❌ Failed to delete webhook: {result.get('description')}")
            return False
    else:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")
        return False

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python set_webhook.py set     - Set webhook")
        print("  python set_webhook.py info    - Get webhook info")
        print("  python set_webhook.py delete  - Delete webhook")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    bot_token = get_bot_token()
    
    if command == "set":
        webhook_url = get_webhook_url()
        secret_token = os.getenv('WEBHOOK_SECRET')
        success = set_webhook(bot_token, webhook_url, secret_token)
        if success:
            print("\n🔍 Verifying webhook...")
            get_webhook_info(bot_token)
    
    elif command == "info":
        get_webhook_info(bot_token)
    
    elif command == "delete":
        delete_webhook(bot_token)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 