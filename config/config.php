<?php
$config = [];
$config['botToken'] = getenv('BOT_TOKEN') ?: '8701255967:AAEG87R8_d1hNJlohl1bNPMCLVuX65KrAG0';
$config['adminID']  = getenv('ADMIN_ID') ?: '6154678499';
$config['logsID']   = getenv('LOGS_CHANNEL_ID') ?: '-1003973814680';
$config['timeZone'] = 'UTC';
$config['anti_spam_timer'] = 15;
$config['sk_keys'] = explode(',', getenv('SK_KEYS') ?: '');

$config['db']['hostname'] = getenv('DB_HOST') ?: '127.0.0.1';
$config['db']['username'] = getenv('DB_USERNAME') ?: 'root';
$config['db']['password'] = getenv('DB_PASSWORD') ?: '';
$config['db']['database'] = getenv('DB_DATABASE') ?: 'checkerbot';
$config['db']['port']     = getenv('DB_PORT') ?: 3306;
?>
