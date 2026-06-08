#!/usr/bin/env python3
"""
ENI Premium Card Checker Bot
صُنع بـ ❤️ من ENI لـ LO
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import CONFIG, OWNER_ID
import database as db
import gateways

# ==========================================
# إعداد Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ENI_CC_BOT")

# ==========================================
# البوت
# ==========================================
storage = MemoryStorage()
bot = Bot(token=CONFIG["BOT_TOKEN"])
dp = Dispatcher(storage=storage)

# ==========================================
# States
# ==========================================
class AddVIP(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

class CheckCard(StatesGroup):
    waiting_card = State()

# ==========================================
# الأوامر
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """البداية"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # إضافة المستخدم
    db.add_user(user_id, username, is_owner=(user_id == OWNER_ID))
    
    is_owner_status = db.is_owner(user_id)
    is_vip_status = db.is_vip(user_id)
    
    if not is_owner_status and not is_vip_status:
        await message.answer(
            "⛔️ **وصول مرفوض**\n\n"
            "هذا البوت خاص.\n"
            f"Your ID: `{user_id}`\n\n"
            "تواصل مع المطور.",
            parse_mode="Markdown"
        )
        return
    
    keyboard = []
    
    if is_vip_status or is_owner_status:
        keyboard.append([InlineKeyboardButton(text="🔍 فحص بطاقة", callback_data="check_card")])
        keyboard.append([InlineKeyboardButton(text="📊 إحصائياتي", callback_data="my_stats")])
    
    if is_owner_status:
        keyboard.append([InlineKeyboardButton(text="👥 إدارة VIP", callback_data="manage_vip")])
        keyboard.append([InlineKeyboardButton(text="📋 المستخدمين", callback_data="list_users")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    status_text = "👑 **المالك**" if is_owner_status else "⭐️ **VIP**"
    
    await message.answer(
        f"👾 **ENI Premium CC Checker**\n\n"
        f"{status_text}\n"
        f"مرحباً {message.from_user.first_name}!\n\n"
        f"اختر من القائمة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==========================================
# فحص البطاقة
# ==========================================

@dp.callback_query(F.data == "check_card")
async def select_gateway(callback: CallbackQuery):
    """اختيار البوابة"""
    user_id = callback.from_user.id
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        await callback.answer("⛔️ تحتاج VIP", show_alert=True)
        return
    
    available_gateways = gateways.get_available_gateways()
    
    keyboard = []
    for gw in available_gateways:
        emoji = "🔵" if gw == "stripe" else "🟢"
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {gw.upper()}",
            callback_data=f"gateway_{gw}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "🔧 **اختر البوابة:**\n\n"
        "البوابات المتاحة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("gateway_"))
async def start_check(callback: CallbackQuery, state: FSMContext):
    """بدء الفحص"""
    gateway_name = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway_name)
    await state.set_state(CheckCard.waiting_card)
    
    await callback.message.edit_text(
        f"💳 **الفحص على {gateway_name.upper()}**\n\n"
        f"أرسل البطاقة:\n"
        f"`1234567890123456|12|2025|123`\n\n"
        f"أو /cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(CheckCard.waiting_card)
async def process_card(message: Message, state: FSMContext):
    """معالجة البطاقة"""
    user_id = message.from_user.id
    card = message.text.strip()
    
    if not '|' in card:
        await message.answer("⚠️ صيغة خاطئة:\n`1234|12|25|123`", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    gateway_name = data.get('gateway', 'stripe')
    
    checking_msg = await message.answer(
        f"⏳ **جاري الفحص...**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway_name.upper()}\n",
        parse_mode="Markdown"
    )
    
    # الفحص
    start_time = time.time()
    status, message_text, _ = gateways.check_card(gateway_name, card)
    elapsed = time.time() - start_time
    
    # حفظ
    db.save_check(user_id, card, gateway_name, status, message_text)
    
    # الرد
    if status == "CHARGED":
        emoji = "🎉"
    elif status == "APPROVED":
        emoji = "✅"
    else:
        emoji = "❌"
    
    result_text = (
        f"{emoji} **النتيجة**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway_name.upper()}\n"
        f"📊 {status}\n"
        f"📝 {message_text}\n"
        f"⏱ {elapsed:.2f}s\n\n"
        f"By @{message.from_user.username or 'Unknown'}"
    )
    
    await checking_msg.edit_text(result_text, parse_mode="Markdown")
    await state.clear()

@dp.message(Command("cancel"))
async def cancel_check(message: Message, state: FSMContext):
    """إلغاء"""
    await state.clear()
    await message.answer("✅ تم الإلغاء")

# ==========================================
# إدارة VIP
# ==========================================

@dp.callback_query(F.data == "manage_vip")
async def manage_vip(callback: CallbackQuery):
    """إدارة VIP"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="➕ إضافة VIP", callback_data="add_vip")],
        [InlineKeyboardButton(text="➖ إزالة VIP", callback_data="remove_vip")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "👥 **إدارة VIP**\n\n"
        "اختر إجراء:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "add_vip")
async def add_vip_start(callback: CallbackQuery, state: FSMContext):
    """بدء إضافة VIP"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    await state.set_state(AddVIP.waiting_user_id)
    await callback.message.edit_text(
        "👤 **إضافة VIP**\n\n"
        "أرسل ID المستخدم:",
        parse_mode="Markdown"
    )

@dp.message(AddVIP.waiting_user_id)
async def add_vip_get_days(message: Message, state: FSMContext):
    """عدد الأيام"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(vip_user_id=user_id)
        await state.set_state(AddVIP.waiting_days)
        await message.answer(
            f"📅 **عدد أيام VIP؟**\n\n"
            f"للمستخدم: `{user_id}`\n"
            f"أرسل الأيام:",
            parse_mode="Markdown"
        )
    except:
        await message.answer("⚠️ ID غير صحيح")

@dp.message(AddVIP.waiting_days)
async def add_vip_confirm(message: Message, state: FSMContext):
    """تأكيد VIP"""
    try:
        days = int(message.text.strip())
        data = await state.get_data()
        user_id = data['vip_user_id']
        
        db.add_vip(user_id, days)
        
        until_date = datetime.now() + timedelta(days=days)
        
        await message.answer(
            f"✅ **تم إضافة VIP**\n\n"
            f"👤 `{user_id}`\n"
            f"📅 {days} يوم\n"
            f"📆 ينتهي: {until_date.strftime('%Y-%m-%d')}",
            parse_mode="Markdown"
        )
        
        # إشعار المستخدم
        try:
            await bot.send_message(
                user_id,
                f"🎉 **تم تفعيل VIP!**\n\n"
                f"المدة: {days} يوم\n"
                f"يمكنك الآن استخدام البوت!",
                parse_mode="Markdown"
            )
        except:
            pass
        
        await state.clear()
    except:
        await message.answer("⚠️ عدد غير صحيح")

# ==========================================
# الإحصائيات
# ==========================================

@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    """إحصائيات المستخدم"""
    user_id = callback.from_user.id
    total, charged, approved = db.get_user_stats(user_id)
    
    text = (
        f"📊 **إحصائياتك**\n\n"
        f"🔢 الفحوصات: {total}\n"
        f"🎉 Charged: {charged}\n"
        f"✅ Approved: {approved}\n"
        f"❌ Declined: {total - charged - approved}"
    )
    
    keyboard = [[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    """قائمة المستخدمين"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    users = db.get_all_users()
    
    text = "👥 **المستخدمين:**\n\n"
    for user_id, username, is_vip_status, vip_until, total_checks in users:
        status = "⭐️ VIP" if is_vip_status else "👤"
        text += f"{status} {username} (`{user_id}`) - {total_checks} فحص\n"
    
    keyboard = [[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """رجوع"""
    await cmd_start(callback.message)

# ==========================================
# التشغيل
# ==========================================
async def main():
    db.init_db()
    logger.info(f"🚀 البوت بدأ - Owner ID: {OWNER_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 إيقاف...")
