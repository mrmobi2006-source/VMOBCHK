"""
نظام قاعدة البيانات المحسّن - Analytics متقدم و Caching
صُنع بـ ❤️ من ENI - Enhanced Edition
"""

import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("premium_bot.db")

def init_db():
    """إنشاء قاعدة البيانات مع جداول محسّنة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول المستخدمين المحسّن
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_owner BOOLEAN DEFAULT 0,
            is_vip BOOLEAN DEFAULT 0,
            vip_until REAL DEFAULT 0,
            added_at REAL,
            total_checks INTEGER DEFAULT 0,
            charged_count INTEGER DEFAULT 0,
            approved_count INTEGER DEFAULT 0,
            declined_count INTEGER DEFAULT 0,
            last_check_time REAL DEFAULT 0,
            is_blocked BOOLEAN DEFAULT 0
        )
    """)
    
    # جدول الفحوصات المحسّن
    c.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card TEXT,
            gateway TEXT,
            status TEXT,
            message TEXT,
            timestamp REAL,
            response_time REAL
        )
    """)
    
    # جدول الإحصائيات اليومية
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            total_checks INTEGER DEFAULT 0,
            charged_count INTEGER DEFAULT 0,
            approved_count INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

# ==================== USER MANAGEMENT ====================

def add_user(user_id, username, is_owner=False):
    """إضافة مستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, username, is_owner, added_at)
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
    
    if is_vip_status and vip_until > 0:
        if time.time() > vip_until:
            remove_vip(user_id)
            return False
        return True
    
    return is_vip_status

def is_blocked(user_id):
    """التحقق من حظر المستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def block_user(user_id):
    """حظر مستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ==================== VIP MANAGEMENT ====================

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

def get_vip_expiry(user_id):
    """الحصول على موعد انتهاء VIP"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row and row[0] > 0:
        return row[0]
    return 0

# ==================== CHECK MANAGEMENT ====================

def save_check(user_id, card, gateway, status, message, response_time=0):
    """حفظ فحص مع وقت الاستجابة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timestamp = time.time()
    
    c.execute("""
        INSERT INTO checks 
        (user_id, card, gateway, status, message, timestamp, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, card, gateway, status, message, timestamp, response_time))
    
    # تحديث إحصائيات المستخدم
    if status == 'CHARGED':
        c.execute("UPDATE users SET charged_count = charged_count + 1 WHERE user_id = ?", (user_id,))
    elif status == 'APPROVED':
        c.execute("UPDATE users SET approved_count = approved_count + 1 WHERE user_id = ?", (user_id,))
    elif status == 'DECLINED':
        c.execute("UPDATE users SET declined_count = declined_count + 1 WHERE user_id = ?", (user_id,))
    
    c.execute("UPDATE users SET total_checks = total_checks + 1 WHERE user_id = ?", (user_id,))
    
    # تحديث الإحصائيات اليومية
    date_str = datetime.now().strftime('%Y-%m-%d')
    c.execute("""
        INSERT INTO daily_stats (date, total_checks)
        VALUES (?, 1)
        ON CONFLICT(date) DO UPDATE SET total_checks = total_checks + 1
    """, (date_str,))
    
    conn.commit()
    conn.close()

# ==================== STATISTICS ====================

def get_user_stats(user_id):
    """إحصائيات المستخدم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT total_checks, charged_count, approved_count, declined_count
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        total, charged, approved, declined = row
        return total, charged, approved, declined
    return 0, 0, 0, 0

def get_global_stats():
    """الإحصائيات العامة للبوت"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # إجمالي الفحوصات
    c.execute("SELECT SUM(total_checks) FROM users")
    total_checks = c.fetchone()[0] or 0
    
    # إجمالي المستخدمين
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # المستخدمين النشطين اليوم
    c.execute("""
        SELECT COUNT(DISTINCT user_id) FROM checks
        WHERE timestamp > ?
    """, (time.time() - 86400,))
    active_today = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total_checks': total_checks,
        'total_users': total_users,
        'active_today': active_today
    }

# ==================== USER MANAGEMENT ====================

def get_all_users():
    """جلب كل المستخدمين مع تفاصيلهم"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, is_vip, vip_until, total_checks, charged_count, is_blocked
        FROM users
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_vip_users():
    """الحصول على مستخدمي VIP النشطين"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, vip_until, total_checks
        FROM users
        WHERE is_vip = 1 AND vip_until > ?
        ORDER BY vip_until DESC
    """, (time.time(),))
    rows = c.fetchall()
    conn.close()
    return rows

def check_rate_limit(user_id, max_checks_per_minute=60):
    """التحقق من حد معدل الفحص"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT COUNT(*) FROM checks
        WHERE user_id = ? AND timestamp > ?
    """, (user_id, time.time() - 60))
    
    count = c.fetchone()[0]
    conn.close()
    
    return count < max_checks_per_minute
