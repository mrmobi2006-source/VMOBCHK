"""
نظام قاعدة البيانات - Users, VIP, Gateways
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("premium_bot.db")

def init_db():
    """إنشاء قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_owner BOOLEAN DEFAULT 0,
            is_vip BOOLEAN DEFAULT 0,
            vip_until REAL DEFAULT 0,
            added_at REAL,
            total_checks INTEGER DEFAULT 0
        )
    """)
    
    # جدول البوابات
    c.execute("""
        CREATE TABLE IF NOT EXISTS gateways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            type TEXT,
            enabled BOOLEAN DEFAULT 1,
            added_by INTEGER,
            added_at REAL,
            config TEXT
        )
    """)
    
    # جدول الفحوصات
    c.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card TEXT,
            gateway TEXT,
            status TEXT,
            message TEXT,
            timestamp REAL
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(user_id, username, is_owner=False):
    """إضافة مستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, is_owner, added_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, is_owner, time.time()))
    conn.commit()
    conn.close()

def is_owner(user_id):
    """التحقق من Owner"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_owner FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def is_vip(user_id):
    """التحقق من VIP"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_vip, vip_until FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return False
    
    is_vip_status, vip_until = row
    
    # التحقق من انتهاء VIP
    if is_vip_status and vip_until > 0:
        if time.time() > vip_until:
            # انتهى VIP
            remove_vip(user_id)
            return False
        return True
    
    return is_vip_status

def add_vip(user_id, days):
    """إضافة VIP لمستخدم"""
    vip_until = time.time() + (days * 86400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET is_vip = 1, vip_until = ? 
        WHERE user_id = ?
    """, (vip_until, user_id))
    conn.commit()
    conn.close()

def remove_vip(user_id):
    """إزالة VIP"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET is_vip = 0, vip_until = 0 
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """جلب كل المستخدمين"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, is_vip, vip_until, total_checks FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def add_gateway(name, gateway_type, config, added_by):
    """إضافة بوابة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO gateways (name, type, enabled, added_by, added_at, config)
            VALUES (?, ?, 1, ?, ?, ?)
        """, (name, gateway_type, added_by, time.time(), config))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def get_all_gateways():
    """جلب كل البوابات"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, type, enabled FROM gateways ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows

def toggle_gateway(name):
    """تفعيل/تعطيل بوابة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE gateways SET enabled = NOT enabled WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def delete_gateway(name):
    """حذف بوابة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM gateways WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def save_check(user_id, card, gateway, status, message):
    """حفظ فحص"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO checks (user_id, card, gateway, status, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, card, gateway, status, message, time.time()))
    
    # تحديث عداد الفحوصات
    c.execute("""
        UPDATE users 
        SET total_checks = total_checks + 1 
        WHERE user_id = ?
    """, (user_id,))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    """إحصائيات المستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # إجمالي الفحوصات
    c.execute("SELECT total_checks FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    total = row[0] if row else 0
    
    # Charged
    c.execute("SELECT COUNT(*) FROM checks WHERE user_id = ? AND status = 'CHARGED'", (user_id,))
    charged = c.fetchone()[0]
    
    # Approved
    c.execute("SELECT COUNT(*) FROM checks WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
    approved = c.fetchone()[0]
    
    conn.close()
    return total, charged, approved
