<?php
require __DIR__ . "/../functions/bot.php";
function capture($s,$start,$end){ $a=explode($start,$s); $a=explode($end,$a[1]); return $a[0]; }
function logsummary($t){ global $config; bot('sendmessage',['chat_id'=>$config['logsID'],'text'=>$t,'parse_mode'=>'html']); }
function add_days($t,$d){ return $t+(60*60*24*str_replace('d','',$d)); }
function add_minutes($t,$m){ return $t+(60*str_replace('m','',$m)); }
function multiexplode($d,$s){ return explode($d[0],str_replace($d,$d[0],$s)); }
function array_in_string($s,$a){ foreach($a as $v) if(stripos($s,$v)!==false) return true; return false; }
?>
