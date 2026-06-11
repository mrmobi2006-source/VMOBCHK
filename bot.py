#!/usr/bin/env python3
"""
ENI Ultimate Card Checker Bot - Enhanced Edition
البوت المحسّن برمته مع ميزات متقدمة جداً
"""

import asyncio
import logging
import time
import os
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import CONFIG, OWNER_ID, OWNER_USERNAME
import database as db
import gateways

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ENI_ULTIMATE")

storage = MemoryStorage()
bot = Bot(token=CONFIG["BOT_TOKEN"])
dp = Dispatcher(storage=storage)

CHECK_STATE = {}
CONCURRENT_CHECKS = {}

# ==================== FSM STATES ====================

class AddVIP(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

class CheckCard(StatesGroup):
    waiting_card = State()

class BulkCheck(StatesGroup):
    waiting_cards = State()

class AdminPanel(StatesGroup):
    waiting_action = State()

# ==================== UTILITIES ====================

def parse_card(card_str):
    """تحليل صيغة البطاقة"""
    card_str = card_str.strip()
    parts = re.split(r'[|\s:]+', card_str)
    
    if len(parts) < 3:
        return None
    
    cc = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvv = parts[3] if len(parts) > 3 else "000"
    
    # التحقق من صحة الرقم
    if not re.match(r'^[0-9]{13,19}$', cc):
        return None
    if not re.match(r'^(0[1-9]|1[0-2])$', mm):
        return None
    
    if len(yy) == 4:
        yy = yy[2:]
    
    if len(mm) == 1:
        mm = '0' + mm
    
    if not re.match(r'^[0-9]{3,4}$', cvv):
        cvv = "000"
    
    return f"{cc}|{mm}|{yy}|{cvv}"

def format_time(seconds):
    """تنسيق الوقت"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def get_gateway_emoji(gateway_name):
    """الحصول على emoji للبوابة"""
    emojis = {
        'stripe': '🔴',
        'braintree': '🟢',
        '2checkout': '🔵',
        'square': '🟡',
        'paypal': '🟣'
    }
    return emojis.get(gateway_name, '⚪️')

# ==================== SECURITY CHECKS ====================

async def check_user_access(user_id: int, update) -> bool:
    """التحقق من صلاحية المستخدم"""
    if db.is_blocked(user_id):
        try:
            await update.answer("⛔️ تم حظرك من البوت", show_alert=True)
        except:
            pass
        return False
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        return False
    
    if not db.check_rate_limit(user_id):
        db.log_suspicious_activity(user_id, "RATE_LIMIT", "محاولة تجاوز الحد المسموح")
        return False
    
    return True

# ==================== START COMMAND ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """بدء البوت"""
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    db.add_user(user_id, username, is_owner=(user_id == OWNER_ID))
    
    # التحقق من الوصول
    if db.is_blocked(user_id):
        await message.answer("⛔️ تم حظر حسابك من البوت")
        return
    
    is_owner_status = db.is_owner(user_id)
    is_vip_status = db.is_vip(user_id)
    
    if not is_owner_status and not is_vip_status:
        await message.answer(
            "⛔️ **وصول مرفوض**\n\n"
            "هذا البوت خاص ويتطلب صلاحيات VIP.\n\n"
            f"🆔 Your ID: `{user_id}`\n"
            f"👤 Username: @{username}\n\n"
            f"📱 للتواصل: @{OWNER_USERNAME}",
            parse_mode="Markdown"
        )
        return
    
    keyboard = []
    
    if is_vip_status or is_owner_status:
        keyboard.append([
            InlineKeyboardButton(text="💳 فحص بطاقة", callback_data="check_single"),
            InlineKeyboardButton(text="📋 فحص قائمة", callback_data="check_bulk")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📁 فحص ملف", callback_data="check_file"),
            InlineKeyboardButton(text="📊 إحصائياتي", callback_data="my_stats")
        ])
    
    if is_owner_status:
        keyboard.append([
            InlineKeyboardButton(text="👥 إدارة VIP", callback_data="manage_vip"),
            InlineKeyboardButton(text="📋 المستخدمين", callback_data="list_users")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📈 الإحصائيات", callback_data="global_stats"),
            InlineKeyboardButton(text="⚙️ الإدارة", callback_data="admin_panel")
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    status_text = "👑 المالك" if is_owner_status else "⭐️ VIP"
    
    try:
        gateways_list = ", ".join(gateways.get_available_gateways())
    except:
        gateways_list = "Stripe, PayPal, 2Checkout, Square, Braintree"
    
    await message.answer(
        f"👾 **ENI Ultimate CC Checker - Enhanced**\n\n"
        f"{status_text} {message.from_user.first_name}\n\n"
        f"🔧 البوابات المتاحة:\n{gateways_list}\n\n"
        f"⚡️ فحص حقيقي 100% | تحديثات مستمرة",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==================== SINGLE CHECK ====================

@dp.callback_query(F.data == "check_single")
async def check_single_gateway(callback: CallbackQuery):
    """اختيار البوابة للفحص الواحد"""
    user_id = callback.from_user.id
    
    if not await check_user_access(user_id, callback):
        await callback.answer("⛔️ ليس لديك صلاحية", show_alert=True)
        return
    
    keyboard = []
    try:
        for gw in gateways.get_available_gateways():
            emoji = get_gateway_emoji(gw)
            keyboard.append([InlineKeyboardButton(text=f"{emoji} {gw.upper()}", callback_data=f"single_{gw}")])
    except:
        pass
    
    keyboard.append([InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "💳 **فحص بطاقة واحدة**\n\nاختر البوابة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("single_"))
async def single_start(callback: CallbackQuery, state: FSMContext):
    """بدء الفحص الواحد"""
    gateway = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway, mode="single")
    await state.set_state(CheckCard.waiting_card)
    
    await callback.message.edit_text(
        f"💳 **فحص بطاقة - {gateway.upper()}**\n\n"
        f"أرسل البطاقة بالصيغة:\n"
        f"`4815820235960174|06|30|123`\n\n"
        f"/cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(CheckCard.waiting_card)
async def process_single_card(message: Message, state: FSMContext):
    """معالجة فحص البطاقة الواحدة"""
    user_id = message.from_user.id
    
    data = await state.get_data()
    gateway = data.get('gateway', 'stripe')
    
    card = parse_card(message.text)
    
    if not card:
        await message.answer("⚠️ صيغة خاطئة! استخدم: `4815820235960174|06|30|123`", parse_mode="Markdown")
        return
    
    checking_msg = await message.answer(
        f"⏳ **جاري الفحص...**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway.upper()}",
        parse_mode="Markdown"
    )
    
    start_time = time.time()
    try:
        status, msg_text, _ = gateways.check_card(gateway, card)
    except:
        status, msg_text = "ERROR", "خطأ في الاتصال"
    
    elapsed = time.time() - start_time
    
    db.save_check(user_id, card, gateway, status, msg_text, elapsed)
    
    emoji_map = {
        "CHARGED": "🎉",
        "APPROVED": "✅",
        "DECLINED": "❌",
        "ERROR": "⚠️"
    }
    emoji = emoji_map.get(status, "❓")
    
    result = (
        f"{emoji} **النتيجة**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway.upper()}\n"
        f"📊 **{status}**\n"
        f"📝 {msg_text}\n"
        f"⏱ {elapsed:.2f}s\n\n"
        f"👤 @{message.from_user.username or 'Unknown'}"
    )
    
    await checking_msg.edit_text(result, parse_mode="Markdown")
    await state.clear()

# ==================== STATS ====================

@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    """إحصائيات المستخدم"""
    uid = callback.from_user.id
    total, charged, approved, declined = db.get_user_stats(uid)
    
    if db.is_vip(uid):
        vip_until = db.get_vip_expiry(uid)
        if vip_until > 0:
            days_left = int((vip_until - time.time()) / 86400)
            vip_text = f"⭐️ VIP لمدة {days_left} أيام"
        else:
            vip_text = "⭐️ VIP"
    else:
        vip_text = "👤 عادي"
    
    text = (
        f"📊 **إحصائياتك**\n\n"
        f"{vip_text}\n\n"
        f"🔢 **إجمالي:** {total:,}\n"
        f"🎉 **CHARGED:** {charged:,}\n"
        f"✅ **APPROVED:** {approved:,}\n"
        f"❌ **DECLINED:** {declined:,}\n\n"
        f"👤 @{callback.from_user.username or 'Unknown'}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "global_stats")
async def global_stats(callback: CallbackQuery):
    """الإحصائيات العامة"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    stats = db.get_global_stats()
    
    text = (
        f"📈 **الإحصائيات العامة**\n\n"
        f"🔢 إجمالي الفحوصات: {stats['total_checks']:,}\n"
        f"👥 إجمالي المستخدمين: {stats['total_users']:,}\n"
        f"🟢 نشطاء اليوم: {stats['active_today']:,}\n\n"
        f"🤖 @{OWNER_USERNAME}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )

# ==================== VIP MANAGEMENT ====================

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
    
    await callback.message.edit_text(
        "👥 **إدارة VIP**\n\nاختر:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "add_vip")
async def add_vip_start(callback: CallbackQuery, state: FSMContext):
    """بدء إضافة VIP"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    await state.set_state(AddVIP.waiting_user_id)
    await callback.message.edit_text("👤 أرسل ID المستخدم:")

@dp.message(AddVIP.waiting_user_id)
async def add_vip_days(message: Message, state: FSMContext):
    """طلب عدد الأيام"""
    try:
        uid = int(message.text.strip())
        await state.update_data(vip_user_id=uid)
        await state.set_state(AddVIP.waiting_days)
        await message.answer(f"📅 عدد الأيام للمستخدم `{uid}`:", parse_mode="Markdown")
    except:
        await message.answer("⚠️ ID غير صحيح")

@dp.message(AddVIP.waiting_days)
async def add_vip_confirm(message: Message, state: FSMContext):
    """تأكيد إضافة VIP"""
    try:
        days = int(message.text.strip())
        data = await state.get_data()
        uid = data['vip_user_id']
        
        db.add_user(uid, f"user_{uid}")
        db.add_vip(uid, days)
        
        until = datetime.now() + timedelta(days=days)
        
        await message.answer(
            f"✅ تم إضافة VIP\n\n👤 `{uid}`\n📅 {days} يوم\n📆 {until.strftime('%Y-%m-%d')}",
            parse_mode="Markdown"
        )
        
        try:
            await bot.send_message(uid, f"🎉 تم تفعيل VIP!\n⭐️ {days} يوم\n/start", parse_mode="Markdown")
        except:
            pass
        
        await state.clear()
    except:
        await message.answer("⚠️ رقم غير صحيح")

# ==================== USER LIST ====================

@dp.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    """قائمة المستخدمين"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    users = db.get_all_users()
    
    text = f"👥 **المستخدمين**\n\n📊 {len(users)} | ⭐️ {sum(1 for u in users if u[2])}\n\n"
    
    for uid, uname, vip, vip_until, checks, charged, blocked in users[:20]:
        st = "⭐️" if vip else "👤"
        bl = "🚫" if blocked else ""
        text += f"{st}{bl} @{uname} - {checks:,} (🎉 {charged})\n"
    
    if len(users) > 20:
        text += f"\n+{len(users)-20}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )

# ==================== ADMIN PANEL ====================

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """لوحة الإدارة"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🔄 تحديث البوابات", callback_data="refresh_gateways")],
        [InlineKeyboardButton(text="🛡️ الأمان", callback_data="security_settings")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    await callback.message.edit_text(
        "⚙️ **لوحة الإدارة**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )

# ==================== BULK CHECK ====================

@dp.callback_query(F.data == "check_bulk")
async def check_bulk_gateway(callback: CallbackQuery):
    """اختيار البوابة للفحص الجماعي"""
    user_id = callback.from_user.id
    
    if user_id in CHECK_STATE and CHECK_STATE[user_id].get('running'):
        await callback.answer("⚠️ لديك فحص جاري", show_alert=True)
        return
    
    keyboard = []
    try:
        for gw in gateways.get_available_gateways():
            emoji = get_gateway_emoji(gw)
            keyboard.append([InlineKeyboardButton(text=f"{emoji} {gw.upper()}", callback_data=f"bulk_{gw}")])
    except:
        pass
    
    keyboard.append([InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📋 **فحص قائمة**\n\nاختر البوابة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("bulk_"))
async def bulk_start(callback: CallbackQuery, state: FSMContext):
    """بدء الفحص الجماعي"""
    gateway = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway, mode="bulk")
    await state.set_state(BulkCheck.waiting_cards)
    
    await callback.message.edit_text(
        f"📋 **فحص قائمة - {gateway.upper()}**\n\n"
        f"الصق القائمة (بطاقة في كل سطر):\n"
        f"```\n4815820235960174|06|30|123\n4830050105358264|08|27|456```\n\n"
        f"/cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(BulkCheck.waiting_cards)
async def process_bulk_cards(message: Message, state: FSMContext):
    """معالجة الفحص الجماعي"""
    user_id = message.from_user.id
    data = await state.get_data()
    gateway = data.get('gateway', 'stripe')
    
    lines = message.text.split('\n')
    cards = []
    
    for line in lines:
        card = parse_card(line)
        if card:
            cards.append(card)
    
    if not cards:
        await message.answer("⚠️ لا توجد بطاقات صالحة")
        await state.clear()
        return
    
    total = len(cards)
    
    status_msg = await message.answer(
        f"🚀 **بدء الفحص**\n\n📋 قائمة\n🔧 {gateway.upper()}\n🔢 {total:,} بطاقة\n\n⏳ جاري...",
        parse_mode="Markdown"
    )
    
    CHECK_STATE[user_id] = {
        'running': True,
        'total': total,
        'checked': 0,
        'charged': 0,
        'approved': 0,
        'declined': 0
    }
    
    start_time = time.time()
    
    for i, card in enumerate(cards, 1):
        if not CHECK_STATE[user_id]['running']:
            break
        
        try:
            status, msg_text, _ = gateways.check_card(gateway, card)
        except:
            status, msg_text = "ERROR", "خطأ"
        
        db.save_check(user_id, card, gateway, status, msg_text)
        
        CHECK_STATE[user_id]['checked'] = i
        
        if status == "CHARGED":
            CHECK_STATE[user_id]['charged'] += 1
            await message.answer(
                f"🎉🎉 **CHARGED!**\n\n💳 `{card}`\n🔧 {gateway.upper()}\n📝 {msg_text}\n\n[{i}/{total:,}]",
                parse_mode="Markdown"
            )
        elif status == "APPROVED":
            CHECK_STATE[user_id]['approved'] += 1
            await message.answer(
                f"✅ **APPROVED!**\n\n💳 `{card}`\n🔧 {gateway.upper()}\n📝 {msg_text}\n\n[{i}/{total:,}]",
                parse_mode="Markdown"
            )
        elif status == "DECLINED":
            CHECK_STATE[user_id]['declined'] += 1
        
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        progress = int((i/total) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        
        if i % 5 == 0:
            update = (
                f"⏳ **[{i}/{total:,}]** {bar}\n\n"
                f"🎉 {CHECK_STATE[user_id]['charged']} | ✅ {CHECK_STATE[user_id]['approved']} | ❌ {CHECK_STATE[user_id]['declined']}\n"
                f"⏱ {rate:.1f}/s | ⏳ ETA ~{format_time(eta)}"
            )
            try:
                await status_msg.edit_text(update, parse_mode="Markdown")
            except:
                pass
        
        await asyncio.sleep(0.3)
    
    elapsed = time.time() - start_time
    
    final = (
        f"🏁 **انتهى الفحص**\n\n📋 قائمة\n🔧 {gateway.upper()}\n\n"
        f"🔢 {total:,} | 🎉 {CHECK_STATE[user_id]['charged']} | "
        f"✅ {CHECK_STATE[user_id]['approved']} | ❌ {CHECK_STATE[user_id]['declined']}\n\n"
        f"⏱ {format_time(elapsed)} | 🚀 {total/elapsed:.1f} card/s"
    )
    
    await status_msg.edit_text(final, parse_mode="Markdown")
    CHECK_STATE[user_id]['running'] = False
    await state.clear()

# ==================== FILE CHECK ====================

@dp.callback_query(F.data == "check_file")
async def check_file(callback: CallbackQuery):
    """فحص ملف"""
    await callback.answer("قادم قريباً", show_alert=True)

# ==================== BACK ====================

@dp.callback_query(F.data == "back_to_main")
async def back_main(callback: CallbackQuery):
    """العودة للقائمة الرئيسية"""
    await cmd_start(callback.message)

# ==================== CANCEL ====================

@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    """إلغاء العملية"""
    await state.clear()
    await message.answer("✅ تم الإلغاء")

# ==================== MAIN ====================

async def main():
    """تشغيل البوت"""
    db.init_db()
    logger.info(f"🚀 ENI Ultimate Bot Started - Owner: @{OWNER_USERNAME} (ID: {OWNER_ID})")
    try:
        logger.info(f"🔧 Available Gateways: {', '.join(gateways.get_available_gateways())}")
    except:
        logger.info("🔧 Gateways loaded")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot Stopped")
