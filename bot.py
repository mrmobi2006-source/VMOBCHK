async def process_cards_batch(message: Message, state: FSMContext, content: str, filename=None):
    """فحص دفعة من البطاقات"""
    user_id = message.from_user.id
    
    data = await state.get_data()
    gateway = data.get('gateway', 'raystede')  # ← البوابة الافتراضية الجديدة
    
    # ... باقي الكود
    
    for i, card in enumerate(cards, 1):
        if not CHECK_STATE[user_id]['running']:
            break
        
        status, msg_text, _ = gateways.check_card(gateway, card)
        
        db.save_check(user_id, card, gateway, status, msg_text)
        
        CHECK_STATE[user_id]['checked'] = i
        
        if status == "CHARGED":
            CHECK_STATE[user_id]['charged'] += 1
            CHECK_STATE[user_id]['approved_cards'].append(f"{card} | CHARGED | {msg_text}")
            emoji = "🎉"
            
            # ← إرسال رسالة فورية للـ CHARGED
            await message.answer(
                f"🎉🎉🎉 **CHARGED!** 🎉🎉🎉\n\n"
                f"💳 `{card}`\n"
                f"🔧 {gateway.upper()}\n"
                f"📝 {msg_text}\n\n"
                f"[{i}/{total:,}]",
                parse_mode="Markdown"
            )
            
        elif status == "APPROVED":
            CHECK_STATE[user_id]['approved'] += 1
            CHECK_STATE[user_id]['approved_cards'].append(f"{card} | APPROVED | {msg_text}")
            emoji = "✅"
            
            # ← إرسال رسالة فورية للـ APPROVED
            await message.answer(
                f"✅ **APPROVED!**\n\n"
                f"💳 `{card}`\n"
                f"🔧 {gateway.upper()}\n"
                f"📝 {msg_text}\n\n"
                f"[{i}/{total:,}]",
                parse_mode="Markdown"
            )
            
        else:
            CHECK_STATE[user_id]['declined'] += 1
            emoji = "❌"
        
        # ... باقي الكود (تحديث الرسالة الرئيسية)
