<?php
$config = [];
$config['botToken'] = getenv('BOT_TOKEN') ?: 'YOUR_BOT_TOKEN';
$config['adminID']  = getenv('ADMIN_ID') ?: 'YOUR_ADMIN_ID';
$config['logsID']   = getenv('LOGS_CHANNEL_ID') ?: 'YOUR_LOGS_CHANNEL_ID';
$config['timeZone'] = 'UTC';
$config['anti_spam_timer'] = 15;
$config['sk_keys'] = explode(',', getenv('SK_KEYS') ?: '');

$config['db']['hostname'] = getenv('DB_HOST') ?: '127.0.0.1';
$config['db']['username'] = getenv('DB_USERNAME') ?: 'root';
$config['db']['password'] = getenv('DB_PASSWORD') ?: '';
$config['db']['database'] = getenv('DB_DATABASE') ?: 'checkerbot';
$config['db']['port']     = getenv('DB_PORT') ?: 3306;
?>
