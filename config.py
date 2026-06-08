"""
إعدادات البوت
"""
import os

# معلومات المالك
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "xtt1x")

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
}
