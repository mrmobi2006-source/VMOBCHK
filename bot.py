#!/usr/bin/env python3
"""
ENI Premium Card Checker Bot
صُنع بـ ❤️ من ENI لـ LO @xtt1x
"""

import asyncio
import logging
import time
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import CONFIG, OWNER_ID, OWNER_USERNAME
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

# حالة الفحص من ملف
FILE_CHECK_STATE = {}

# ==========================================
# States
# ==========================================
class AddVIP(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

class CheckCard(StatesGroup):
    waiting_card = State()

class FileCheck(StatesGroup):
    waiting_file = State()

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
            InlineKeyboardButton(text="💳 فحص بطاقة", callback_data="check_card"),
            InlineKeyboardButton(text="📁 فحص ملف", callback_data="check_file")
        ])
        keyboard.append([InlineKeyboardButton(text="📊 إحصائياتي", callback_data="my_stats")])
    
    if is_owner_status:
        keyboard.append([
            InlineKeyboardButton(text="👥 إدارة VIP", callback_data="manage_vip"),
            InlineKeyboardButton(text="📋 المستخدمين", callback_data="list_users")
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    status_text = "👑 **المالك**" if is_owner_status else "⭐️ **VIP**"
    
    await message.answer(
        f"👾 **ENI Premium CC Checker**\n\n"
        f"{status_text}\n"
        f"مرحباً {message.from_user.first_name}!\n\n"
        f"🔧 البوابات المتاحة:\n"
        f"  • 🔵 Stripe\n"
        f"  • 🟢 PayPal\n\n"
        f"اختر من القائمة أدناه:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ==========================================
# فحص بطاقة واحدة
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
        "🔧 **اختر البوابة للفحص:**\n\n"
        "🔵 **Stripe** - Friends For Sight\n"
        "🟢 **PayPal** - GraphQL API\n\n"
        "اختر البوابة:",
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
        f"أرسل البطاقة بالصيغة:\n"
        f"`1234567890123456|12|2025|123`\n\n"
        f"أو أرسل /cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(CheckCard.waiting_card)
async def process_card(message: Message, state: FSMContext):
    """معالجة البطاقة"""
    user_id = message.from_user.id
    card = message.text.strip()
    
    if not '|' in card:
        await message.answer("⚠️ صيغة خاطئة. استخدم:\n`1234|12|25|123`", parse_mode="Markdown")
        return
    
    data = await state.get_data()
    gateway_name = data.get('gateway', 'stripe')
    
    checking_msg = await message.answer(
        f"⏳ **جاري الفحص...**\n\n"
        f"💳 `{card}`\n"
        f"🔧 البوابة: **{gateway_name.upper()}**\n"
        f"⚙️ الرجاء الانتظار...",
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
        color = "🟢"
    elif status == "APPROVED":
        emoji = "✅"
        color = "🟡"
    else:
        emoji = "❌"
        color = "🔴"
    
    result_text = (
        f"{emoji} **النتيجة**\n\n"
        f"💳 `{card}`\n"
        f"🔧 البوابة: **{gateway_name.upper()}**\n"
        f"{color} الحالة: **{status}**\n"
        f"📝 الرسالة: {message_text}\n"
        f"⏱ الوقت: {elapsed:.2f}s\n\n"
        f"👤 Checked by: @{message.from_user.username or 'Unknown'}\n"
        f"🤖 Bot by: @{OWNER_USERNAME}"
    )
    
    await checking_msg.edit_text(result_text, parse_mode="Markdown")
    await state.clear()

# ==========================================
# فحص من ملف
# ==========================================

@dp.callback_query(F.data == "check_file")
async def check_file_start(callback: CallbackQuery):
    """بدء فحص من ملف"""
    user_id = callback.from_user.id
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        await callback.answer("⛔️ تحتاج VIP", show_alert=True)
        return
    
    # التحقق من وجود فحص جاري
    if user_id in FILE_CHECK_STATE and FILE_CHECK_STATE[user_id].get('running'):
        await callback.answer("⚠️ لديك فحص جاري بالفعل", show_alert=True)
        return
    
    available_gateways = gateways.get_available_gateways()
    
    keyboard = []
    for gw in available_gateways:
        emoji = "🔵" if gw == "stripe" else "🟢"
        keyboard.append([InlineKeyboardButton(
            text=f"{emoji} {gw.upper()}",
            callback_data=f"filegateway_{gw}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📁 **فحص من ملف**\n\n"
        "اختر البوابة أولاً:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("filegateway_"))
async def file_gateway_selected(callback: CallbackQuery, state: FSMContext):
    """تم اختيار البوابة - انتظار الملف"""
    gateway_name = callback.data.split("_")[1]
    
    await state.update_data(file_gateway=gateway_name)
    await state.set_state(FileCheck.waiting_file)
    
    await callback.message.edit_text(
        f"📁 **فحص ملف - {gateway_name.upper()}**\n\n"
        f"أرسل ملف .txt يحتوي على البطاقات\n"
        f"كل بطاقة في سطر:\n\n"
        f"```\n"
        f"1234567890123456|12|25|123\n"
        f"9876543210987654|01|26|456\n"
        f"```\n\n"
        f"أو /cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(FileCheck.waiting_file, F.document)
async def process_file(message: Message, state: FSMContext):
    """معالجة الملف"""
    user_id = message.from_user.id
    
    # التحقق من نوع الملف
    if not message.document.file_name.endswith('.txt'):
        await message.answer("⚠️ أرسل ملف .txt فقط")
        return
    
    # تحميل الملف
    file_info = await bot.get_file(message.document.file_id)
    file_path = file_info.file_path
    
    # تحميل محتوى الملف
    downloaded_file = await bot.download_file(file_path)
    file_content = downloaded_file.read().decode('utf-8')
    
    # استخراج البطاقات
    cards = [line.strip() for line in file_content.split('\n') if line.strip() and '|' in line]
    
    if not cards:
        await message.answer("⚠️ لم يتم العثور على بطاقات صالحة في الملف")
        await state.clear()
        return
    
    data = await state.get_data()
    gateway_name = data.get('file_gateway', 'stripe')
    
    # رسالة البداية
    total_cards = len(cards)
    
    status_msg = await message.answer(
        f"🚀 **بدء الفحص من الملف**\n\n"
        f"📁 الملف: `{message.document.file_name}`\n"
        f"🔧 البوابة: **{gateway_name.upper()}**\n"
        f"🔢 إجمالي البطاقات: **{total_cards}**\n\n"
        f"⏳ جاري الفحص...",
        parse_mode="Markdown"
    )
    
    # حالة الفحص
    FILE_CHECK_STATE[user_id] = {
        'running': True,
        'total': total_cards,
        'checked': 0,
        'charged': 0,
        'approved': 0,
        'declined': 0
    }
    
    # الفحص
    start_time = time.time()
    
    for i, card in enumerate(cards, 1):
        if not FILE_CHECK_STATE[user_id]['running']:
            await status_msg.edit_text(
                f"🛑 **تم إيقاف الفحص**\n\n"
                f"تم فحص {i-1} من {total_cards}",
                parse_mode="Markdown"
            )
            break
        
        # فحص البطاقة
        status, msg_text, _ = gateways.check_card(gateway_name, card)
        
        # حفظ النتيجة
        db.save_check(user_id, card, gateway_name, status, msg_text)
        
        # تحديث الإحصائيات
        FILE_CHECK_STATE[user_id]['checked'] = i
        
        if status == "CHARGED":
            FILE_CHECK_STATE[user_id]['charged'] += 1
            result_emoji = "🎉"
        elif status == "APPROVED":
            FILE_CHECK_STATE[user_id]['approved'] += 1
            result_emoji = "✅"
        else:
            FILE_CHECK_STATE[user_id]['declined'] += 1
            result_emoji = "❌"
        
        # إرسال نتيجة كل بطاقة
        await message.answer(
            f"{result_emoji} **[{i}/{total_cards}]**\n\n"
            f"💳 `{card}`\n"
            f"📊 {status}\n"
            f"📝 {msg_text}",
            parse_mode="Markdown"
        )
        
        # تحديث رسالة الحالة كل 5 بطاقات
        if i % 5 == 0 or i == total_cards:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            
            await status_msg.edit_text(
                f"⚙️ **جاري الفحص...**\n\n"
                f"📊 التقدم: **{i}/{total_cards}** ({i*100//total_cards}%)\n"
                f"🎉 Charged: **{FILE_CHECK_STATE[user_id]['charged']}**\n"
                f"✅ Approved: **{FILE_CHECK_STATE[user_id]['approved']}**\n"
                f"❌ Declined: **{FILE_CHECK_STATE[user_id]['declined']}**\n"
                f"⏱ السرعة: {rate:.1f} card/s\n"
                f"🔧 البوابة: **{gateway_name.upper()}**",
                parse_mode="Markdown"
            )
        
        # انتظار قصير بين البطاقات
        await asyncio.sleep(2)
    
    # النتيجة النهائية
    elapsed = time.time() - start_time
    
    final_text = (
        f"🏁 **انتهى الفحص**\n\n"
        f"📁 الملف: `{message.document.file_name}`\n"
        f"🔧 البوابة: **{gateway_name.upper()}**\n\n"
        f"📊 **النتائج:**\n"
        f"🔢 إجمالي: **{total_cards}**\n"
        f"🎉 Charged: **{FILE_CHECK_STATE[user_id]['charged']}**\n"
        f"✅ Approved: **{FILE_CHECK_STATE[user_id]['approved']}**\n"
        f"❌ Declined: **{FILE_CHECK_STATE[user_id]['declined']}**\n\n"
        f"⏱ الوقت: {elapsed/60:.1f} دقيقة\n"
        f"🚀 السرعة: {total_cards/elapsed:.1f} card/s\n\n"
        f"👤 By: @{message.from_user.username or 'Unknown'}\n"
        f"🤖 Bot: @{OWNER_USERNAME}"
    )
    
    await status_msg.edit_text(final_text, parse_mode="Markdown")
    
    # تنظيف الحالة
    FILE_CHECK_STATE[user_id]['running'] = False
    await state.clear()

@dp.message(Command("stop"))
async def stop_file_check(message: Message):
    """إيقاف فحص الملف"""
    user_id = message.from_user.id
    
    if user_id in FILE_CHECK_STATE and FILE_CHECK_STATE[user_id].get('running'):
        FILE_CHECK_STATE[user_id]['running'] = False
        await message.answer("🛑 جاري إيقاف الفحص...")
    else:
        await message.answer("⚠️ لا يوجد فحص جاري")

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
            f"أرسل عدد الأيام:",
            parse_mode="Markdown"
        )
    except:
        await message.answer("⚠️ ID غير صحيح. أرسل رقم.")

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
            f"✅ **تم إضافة VIP بنجاح**\n\n"
            f"👤 المستخدم: `{user_id}`\n"
            f"📅 المدة: **{days}** يوم\n"
            f"📆 ينتهي: {until_date.strftime('%Y-%m-%d')}\n\n"
            f"🤖 By: @{OWNER_USERNAME}",
            parse_mode="Markdown"
        )
        
        # إشعار للمستخدم
        try:
            await bot.send_message(
                user_id,
                f"🎉 **تم تفعيل VIP!**\n\n"
                f"⭐️ المدة: **{days}** يوم\n"
                f"📆 ينتهي: {until_date.strftime('%Y-%m-%d')}\n\n"
                f"الآن يمكنك استخدام البوت!\n"
                f"أرسل /start للبدء\n\n"
                f"🤖 Bot by: @{OWNER_USERNAME}",
                parse_mode="Markdown"
            )
        except:
            pass
        
        await state.clear()
    except:
        await message.answer("⚠️ عدد أيام غير صحيح.")

@dp.callback_query(F.data == "remove_vip")
async def remove_vip_ask(callback: CallbackQuery, state: FSMContext):
    """إزالة VIP"""
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    await callback.message.edit_text(
        "➖ **إزالة VIP**\n\n"
        "أرسل ID المستخدم لإزالة VIP منه:",
        parse_mode="Markdown"
    )
    
    await state.set_state("waiting_remove_vip")

@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def remove_vip_confirm(message: Message, state: FSMContext):
    """تأكيد إزالة VIP"""
    current_state = await state.get_state()
    
    if current_state == "waiting_remove_vip":
        user_id = int(message.text.strip())
        db.remove_vip(user_id)
        
        await message.answer(
            f"✅ **تم إزالة VIP**\n\n"
            f"👤 المستخدم: `{user_id}`\n"
            f"❌ تم إلغاء صلاحيات VIP",
            parse_mode="Markdown"
        )
        
        await state.clear()

# ==========================================
# الإحصائيات
# ==========================================

@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    """إحصائيات المستخدم"""
    user_id = callback.from_user.id
    total, charged, approved = db.get_user_stats(user_id)
    
    declined = total - charged - approved
    
    text = (
        f"📊 **إحصائياتك**\n\n"
        f"🔢 إجمالي الفحوصات: **{total}**\n"
        f"🎉 Charged: **{charged}**\n"
        f"✅ Approved: **{approved}**\n"
        f"❌ Declined: **{declined}**\n\n"
        f"👤 @{callback.from_user.username or 'Unknown'}\n"
        f"🤖 Bot by: @{OWNER_USERNAME}"
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
    
    text = f"👥 **قائمة المستخدمين**\n\n"
    text += f"📊 الإجمالي: **{len(users)}**\n"
    text += f"⭐️ VIP: **{sum(1 for u in users if u[2])}**\n\n"
    
    for user_id, username, is_vip_status, vip_until, total_checks in users[:20]:
        status = "⭐️" if is_vip_status else "👤"
        vip_text = ""
        if is_vip_status and vip_until > 0:
            days_left = int((vip_until - time.time()) / 86400)
            vip_text = f" ({days_left}d)"
        
        text += f"{status} @{username} - `{user_id}`{vip_text} - {total_checks} checks\n"
    
    if len(users) > 20:
        text += f"\n... و {len(users)-20} آخرين"
    
    text += f"\n\n🤖 Bot by: @{OWNER_USERNAME}"
    
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
    logger.info(f"🚀 البوت بدأ - Owner: @{OWNER_USERNAME} (ID: {OWNER_ID})")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 إيقاف البوت...")
