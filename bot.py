#!/usr/bin/env python3
"""
ENI Ultimate Card Checker Bot
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

class AddVIP(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

class CheckCard(StatesGroup):
    waiting_card = State()

class BulkCheck(StatesGroup):
    waiting_cards = State()

def parse_card(card_str):
    card_str = card_str.strip()
    parts = re.split(r'[|\s]+', card_str)
    
    if len(parts) < 3:
        return None
    
    cc = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvv = parts[3] if len(parts) > 3 else "000"
    
    if len(yy) == 4:
        yy = yy[2:]
    
    if len(mm) == 1:
        mm = '0' + mm
    
    return f"{cc}|{mm}|{yy}|{cvv}"

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
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
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    status_text = "👑 المالك" if is_owner_status else "⭐️ VIP"
    
    await message.answer(
        f"👾 **ENI Ultimate CC Checker**\n\n"
        f"{status_text}\n"
        f"مرحباً {message.from_user.first_name}!\n\n"
        f"🔧 البوابات: Raystede, L-com, Stripe, PayPal\n"
        f"⚡️ فحص حقيقي 100%\n\n"
        f"اختر من القائمة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_single")
async def check_single_gateway(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        await callback.answer("⛔️ تحتاج VIP", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🔵 Raystede", callback_data="single_raystede")],
        [InlineKeyboardButton(text="🟢 L-com", callback_data="single_lcom")],
        [InlineKeyboardButton(text="🔴 Stripe", callback_data="single_stripe")],
        [InlineKeyboardButton(text="🟡 PayPal", callback_data="single_paypal")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "💳 **فحص بطاقة واحدة**\n\naختر البوابة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("single_"))
async def single_start(callback: CallbackQuery, state: FSMContext):
    gateway = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway, mode="single")
    await state.set_state(CheckCard.waiting_card)
    
    await callback.message.edit_text(
        f"💳 **فحص بطاقة - {gateway.upper()}**\n\n"
        f"أرسل البطاقة:\n"
        f"`4815820235960174|06|30`\n\n"
        f"/cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(CheckCard.waiting_card)
async def process_single_card(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    data = await state.get_data()
    gateway = data.get('gateway', 'raystede')
    
    card = parse_card(message.text)
    
    if not card:
        await message.answer("⚠️ صيغة خاطئة", parse_mode="Markdown")
        return
    
    checking_msg = await message.answer(
        f"⏳ **جاري الفحص...**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway.upper()}",
        parse_mode="Markdown"
    )
    
    start_time = time.time()
    status, msg_text, _ = gateways.check_card(gateway, card)
    elapsed = time.time() - start_time
    
    db.save_check(user_id, card, gateway, status, msg_text)
    
    if status == "CHARGED":
        emoji = "🎉"
    elif status == "APPROVED":
        emoji = "✅"
    else:
        emoji = "❌"
    
    result = (
        f"{emoji} **النتيجة**\n\n"
        f"💳 `{card}`\n"
        f"🔧 {gateway.upper()}\n"
        f"📊 **{status}**\n"
        f"📝 {msg_text}\n"
        f"⏱ {elapsed:.2f}s\n\n"
        f"👤 @{message.from_user.username or 'Unknown'}\n"
        f"🤖 @{OWNER_USERNAME}"
    )
    
    await checking_msg.edit_text(result, parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "check_bulk")
async def check_bulk_gateway(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        await callback.answer("⛔️ تحتاج VIP", show_alert=True)
        return
    
    if user_id in CHECK_STATE and CHECK_STATE[user_id].get('running'):
        await callback.answer("⚠️ لديك فحص جاري", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🔵 Raystede", callback_data="bulk_raystede")],
        [InlineKeyboardButton(text="🟢 L-com", callback_data="bulk_lcom")],
        [InlineKeyboardButton(text="🔴 Stripe", callback_data="bulk_stripe")],
        [InlineKeyboardButton(text="🟡 PayPal", callback_data="bulk_paypal")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📋 **فحص قائمة**\n\nاختر البوابة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("bulk_"))
async def bulk_start(callback: CallbackQuery, state: FSMContext):
    gateway = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway, mode="bulk")
    await state.set_state(BulkCheck.waiting_cards)
    
    await callback.message.edit_text(
        f"📋 **فحص قائمة - {gateway.upper()}**\n\n"
        f"الصق القائمة:\n"
        f"```\n4815820235960174|06|30\n4830050105358264|08|27```\n\n"
        f"/cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(BulkCheck.waiting_cards)
async def process_bulk_cards(message: Message, state: FSMContext):
    await process_cards_batch(message, state, message.text)

@dp.callback_query(F.data == "check_file")
async def check_file_gateway(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not db.is_vip(user_id) and not db.is_owner(user_id):
        await callback.answer("⛔️ تحتاج VIP", show_alert=True)
        return
    
    if user_id in CHECK_STATE and CHECK_STATE[user_id].get('running'):
        await callback.answer("⚠️ لديك فحص جاري", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🔵 Raystede", callback_data="file_raystede")],
        [InlineKeyboardButton(text="🟢 L-com", callback_data="file_lcom")],
        [InlineKeyboardButton(text="🔴 Stripe", callback_data="file_stripe")],
        [InlineKeyboardButton(text="🟡 PayPal", callback_data="file_paypal")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        "📁 **فحص من ملف**\n\nاختر البوابة:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("file_"))
async def file_start(callback: CallbackQuery, state: FSMContext):
    gateway = callback.data.split("_")[1]
    
    await state.update_data(gateway=gateway, mode="file")
    await state.set_state("waiting_file")
    
    await callback.message.edit_text(
        f"📁 **فحص ملف - {gateway.upper()}**\n\n"
        f"أرسل ملف .txt\n\n/cancel للإلغاء",
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.document and msg.document.file_name.endswith('.txt'))
async def process_file(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state != "waiting_file":
        return
    
    file_info = await bot.get_file(message.document.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    content = downloaded.read().decode('utf-8', errors='ignore')
    
    await process_cards_batch(message, state, content, filename=message.document.file_name)

async def process_cards_batch(message: Message, state: FSMContext, content: str, filename=None):
    user_id = message.from_user.id
    
    data = await state.get_data()
    gateway = data.get('gateway', 'raystede')
    
    lines = content.split('\n')
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
    
    stop_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 إيقاف", callback_data=f"stop_check_{user_id}")]
    ])
    
    status_msg = await message.answer(
        f"🚀 **بدء الفحص**\n\n"
        f"{'📁 ' + filename if filename else '📋 قائمة'}\n"
        f"🔧 {gateway.upper()}\n"
        f"🔢 {total:,} بطاقة\n\n⏳ جاري...",
        reply_markup=stop_button,
        parse_mode="Markdown"
    )
    
    CHECK_STATE[user_id] = {
        'running': True,
        'total': total,
        'checked': 0,
        'charged': 0,
        'approved': 0,
        'declined': 0,
        'approved_cards': []
    }
    
    start_time = time.time()
    
    for i, card in enumerate(cards, 1):
        if not CHECK_STATE[user_id]['running']:
            await status_msg.edit_text(
                f"🛑 **تم الإيقاف**\n\n"
                f"تم فحص {i-1}/{total:,}",
                parse_mode="Markdown"
            )
            break
        
        status, msg_text, _ = gateways.check_card(gateway, card)
        
        db.save_check(user_id, card, gateway, status, msg_text)
        
        CHECK_STATE[user_id]['checked'] = i
        
        if status == "CHARGED":
            CHECK_STATE[user_id]['charged'] += 1
            CHECK_STATE[user_id]['approved_cards'].append(f"{card} | CHARGED | {msg_text}")
            emoji = "🎉"
            
            await message.answer(
                f"🎉🎉 **CHARGED!**\n\n💳 `{card}`\n🔧 {gateway.upper()}\n📝 {msg_text}\n\n[{i}/{total:,}]",
                parse_mode="Markdown"
            )
            
        elif status == "APPROVED":
            CHECK_STATE[user_id]['approved'] += 1
            CHECK_STATE[user_id]['approved_cards'].append(f"{card} | APPROVED | {msg_text}")
            emoji = "✅"
            
            await message.answer(
                f"✅ **APPROVED!**\n\n💳 `{card}`\n🔧 {gateway.upper()}\n📝 {msg_text}\n\n[{i}/{total:,}]",
                parse_mode="Markdown"
            )
            
        else:
            CHECK_STATE[user_id]['declined'] += 1
            emoji = "❌"
        
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        
        progress = int((i/total) * 20)
        bar = "█" * progress + "░" * (20 - progress)
        
        update = (
            f"{emoji} **[{i}/{total:,}]** {bar}\n\n"
            f"💳 `{card}`\n📊 **{status}**\n📝 {msg_text}\n\n"
            f"🎉 Charged: **{CHECK_STATE[user_id]['charged']}**\n"
            f"✅ Approved: **{CHECK_STATE[user_id]['approved']}**\n"
            f"❌ Declined: **{CHECK_STATE[user_id]['declined']}**\n\n"
            f"⏱ {rate:.1f} card/s | ⏳ ~{format_time(eta)}\n🔧 {gateway.upper()}"
        )
        
        try:
            await status_msg.edit_text(update, reply_markup=stop_button, parse_mode="Markdown")
        except:
            pass
        
        await asyncio.sleep(1.5)
    
    elapsed = time.time() - start_time
    
    final = (
        f"🏁 **انتهى الفحص**\n\n"
        f"{'📁 ' + filename if filename else '📋 قائمة'}\n🔧 {gateway.upper()}\n\n"
        f"🔢 {total:,} | 🎉 {CHECK_STATE[user_id]['charged']} | "
        f"✅ {CHECK_STATE[user_id]['approved']} | ❌ {CHECK_STATE[user_id]['declined']}\n\n"
        f"⏱ {format_time(elapsed)} | 🚀 {total/elapsed:.1f} card/s\n\n"
        f"👤 @{message.from_user.username or 'Unknown'} | 🤖 @{OWNER_USERNAME}"
    )
    
    await status_msg.edit_text(final, parse_mode="Markdown")
    
    if CHECK_STATE[user_id]['approved_cards']:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f"approved_{ts}.txt"
        
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(f"# ENI Ultimate CC Checker\n# Gateway: {gateway.upper()}\n")
            f.write(f"# Total: {len(CHECK_STATE[user_id]['approved_cards'])}\n\n")
            for c in CHECK_STATE[user_id]['approved_cards']:
                f.write(f"{c}\n")
        
        await message.answer_document(
            FSInputFile(fname),
            caption=f"✅ {len(CHECK_STATE[user_id]['approved_cards'])} بطاقة"
        )
        
        os.remove(fname)
    
    CHECK_STATE[user_id]['running'] = False
    await state.clear()

@dp.callback_query(F.data.startswith("stop_check_"))
async def stop_check_button(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("⛔️ ليس فحصك", show_alert=True)
        return
    
    if user_id in CHECK_STATE and CHECK_STATE[user_id].get('running'):
        CHECK_STATE[user_id]['running'] = False
        await callback.answer("🛑 جاري الإيقاف...", show_alert=True)

@dp.message(Command("stop"))
async def stop_check(message: Message):
    user_id = message.from_user.id
    
    if user_id in CHECK_STATE and CHECK_STATE[user_id].get('running'):
        CHECK_STATE[user_id]['running'] = False
        await message.answer("🛑 جاري الإيقاف...")

@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ تم الإلغاء")

@dp.callback_query(F.data == "manage_vip")
async def manage_vip(callback: CallbackQuery):
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="➕ إضافة VIP", callback_data="add_vip")],
        [InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]
    ]
    
    await callback.message.edit_text(
        "👥 **إدارة VIP**\n\nاختر:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "add_vip")
async def add_vip_start(callback: CallbackQuery, state: FSMContext):
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    await state.set_state(AddVIP.waiting_user_id)
    await callback.message.edit_text("👤 أرسل ID المستخدم:")

@dp.message(AddVIP.waiting_user_id)
async def add_vip_days(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        await state.update_data(vip_user_id=uid)
        await state.set_state(AddVIP.waiting_days)
        await message.answer(f"📅 عدد الأيام للمستخدم `{uid}`:", parse_mode="Markdown")
    except:
        await message.answer("⚠️ ID غير صحيح")

@dp.message(AddVIP.waiting_days)
async def add_vip_confirm(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        data = await state.get_data()
        uid = data['vip_user_id']
        
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

@dp.callback_query(F.data == "my_stats")
async def my_stats(callback: CallbackQuery):
    uid = callback.from_user.id
    total, charged, approved = db.get_user_stats(uid)
    
    text = (
        f"📊 **إحصائياتك**\n\n"
        f"🔢 {total:,} | 🎉 {charged:,} | ✅ {approved:,} | ❌ {total-charged-approved:,}\n\n"
        f"👤 @{callback.from_user.username or 'Unknown'} | 🤖 @{OWNER_USERNAME}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "list_users")
async def list_users(callback: CallbackQuery):
    if not db.is_owner(callback.from_user.id):
        await callback.answer("⛔️ للمالك فقط", show_alert=True)
        return
    
    users = db.get_all_users()
    
    text = f"👥 **المستخدمين**\n\n📊 {len(users)} | ⭐️ {sum(1 for u in users if u[2])}\n\n"
    
    for uid, uname, vip, vip_until, checks in users[:15]:
        st = "⭐️" if vip else "👤"
        vtext = ""
        if vip and vip_until > 0:
            days = int((vip_until - time.time()) / 86400)
            vtext = f" ({days}d)"
        
        text += f"{st} @{uname} `{uid}`{vtext} - {checks:,}\n"
    
    if len(users) > 15:
        text += f"\n+{len(users)-15}"
    
    text += f"\n\n🤖 @{OWNER_USERNAME}"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="« رجوع", callback_data="back_to_main")]]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_main")
async def back_main(callback: CallbackQuery):
    await cmd_start(callback.message)

async def main():
    db.init_db()
    logger.info(f"🚀 Bot Started - Owner: @{OWNER_USERNAME} (ID: {OWNER_ID})")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Stopped")
