"""
إعدادات البوت
"""
import os

# Owner ID (ضع Telegram ID الخاص بك هنا)
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_TELEGRAM_ID"))

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN"),
}
