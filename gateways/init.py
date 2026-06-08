"""
Gateway Manager
"""

from . import stripe, paypal

GATEWAYS = {
    'stripe': stripe,
    'paypal': paypal
}

def check_card(gateway_name, card):
    """فحص بطاقة عبر البوابة المحددة"""
    if gateway_name in GATEWAYS:
        return GATEWAYS[gateway_name].check_card(card)
    return "ERROR", "بوابة غير موجودة", ""
