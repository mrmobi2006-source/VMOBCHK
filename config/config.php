<?php
// قراءة بيانات التوكن والآدمن من متغيرات البيئة في Railway
$config['botToken'] = getenv('BOT_TOKEN');
$config['adminID'] = getenv('ADMIN_ID');
$config['logsID'] = getenv('LOGS_CHANNEL_ID');
$config['timeZone'] = 'Asia/Riyadh'; // عدل التوقيت إذا لزم الأمر
$config['anti_spam_timer'] = 15;

// قراءة بيانات قاعدة البيانات (Railway يوفر هذه المتغيرات تلقائياً)
$config['db']['hostname'] = getenv('MYSQLHOST');
$config['db']['username'] = getenv('MYSQLUSER');
$config['db']['password'] = getenv('MYSQLPASSWORD');
$config['db']['database'] = getenv('MYSQLDATABASE');
$config['db']['port'] = getenv('MYSQLPORT') ?: 3306;

// قراءة مفاتيح SK (افصل بينها بفاصلة , في متغيرات Railway)
$config['sk_keys'] = explode(',', getenv('SK_KEYS'));
?>
