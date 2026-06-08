"""
إعدادات البوت
"""
import os

# ضع Telegram ID الخاص بك هنا
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
}
