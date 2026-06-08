# gateways.py

import requests

def check_card(gateway_name: str, card: str):
    """
    gateway_name: اسم البوابة (stripe, braintree, etc.)
    card: "NUMBER|MM|YYYY|CVV"
    returns: (status, message, raw_response)
    """
    try:
        parts = card.strip().split("|")
        if len(parts) != 4:
            return ("DECLINED", "صيغة البطاقة خاطئة", None)
        
        number, month, year, cvv = parts

        # هنا تضع منطق الفحص الفعلي حسب البوابة
        if gateway_name.lower() == "stripe":
            return _check_stripe(number, month, year, cvv)
        elif gateway_name.lower() == "braintree":
            return _check_braintree(number, month, year, cvv)
        else:
            return ("DECLINED", f"بوابة غير معروفة: {gateway_name}", None)

    except Exception as e:
        return ("ERROR", str(e), None)


def _check_stripe(number, month, year, cvv):
    # placeholder — ضع هنا API key وطلب Stripe الفعلي
    return ("DECLINED", "Stripe: غير مفعل بعد", None)


def _check_braintree(number, month, year, cvv):
    # placeholder
    return ("DECLINED", "Braintree: غير مفعل بعد", None)
