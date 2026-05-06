<?php
require __DIR__ . "/config/config.php";
require __DIR__ . "/config/variables.php";
require __DIR__ . "/functions/db.php";
require __DIR__ . "/functions/functions.php";

if(isBanned($userId)){ bot('sendmessage',['chat_id'=>$chat_id,'text'=>'<b>🚫 You are permanently banned.</b>','parse_mode'=>'html','reply_to_message_id'=>$message_id]); exit; }
if(isMuted($userId)) exit;

addUser($userId);

if(strpos($message,"/start")===0 || strpos($message,"!start")===0){
    $msg = "<b>Welcome @$username!\nType /cmds to explore.</b>";
    bot('sendmessage',['chat_id'=>$chat_id,'text'=>$msg,'parse_mode'=>'html','reply_to_message_id'=>$message_id]);
}

if(strpos($message,"/cmds")===0 || strpos($message,"!cmds")===0){
    bot('sendmessage',['chat_id'=>$chat_id,'text'=>'<b>💳 Checker</b>\n/ss | !ss - Stripe Auth\n/sm | !sm - Stripe Merchant\n/schk | !schk - User SK Gate\n/visa | !visa - Visa Status Check\n\n<b>🛠 Tools</b>\n/bin | !bin - BIN Lookup\n/iban | !iban - IBAN Check\n/stats | !stats - Checker Stats\n/apikey sk_live_xxx - Add SK Key\n\n<b>⚙️ Admin</b>\n/admin - Admin Panel','parse_mode'=>'html','reply_to_message_id'=>$message_id]);
}

if($data=="checkergates") bot('editMessageText',['chat_id'=>$callbackchatid,'message_id'=>$callbackmessageid,'text'=>"<b>━━CC & Visa Checker━━</b>\n<b>/ss | !ss - Stripe Auth</b>\n<b>/sm | !sm - Stripe Merchant</b>\n<b>/schk | !schk - User Stripe Gate</b>\n<b>/visa | !visa - Visa Status Check</b>\n<b>/apikey sk_live_xxx - Add SK</b>","reply_markup"=>json_encode(['inline_keyboard'=>[[['text'=>"Return",'callback_data'=>"back"]]])]);
if($data=="othercmds") bot('editMessageText',['chat_id'=>$callbackchatid,'message_id'=>$callbackmessageid,'text'=>"<b>━━Other Commands━━</b>\n<b>/me | !me - Profile</b>\n<b>/stats | !stats - Stats</b>\n<b>/bin | !bin - BIN</b>\n<b>/iban | !iban - IBAN</b>","reply_markup"=>json_encode(['inline_keyboard'=>[[['text'=>"Return",'callback_data'=>"back"]]])]);
if($data=="back") bot('editMessageText',['chat_id'=>$callbackchatid,'message_id'=>$callbackmessageid,'text'=>'<b>Select a category:</b>','reply_markup'=>json_encode(['inline_keyboard'=>[[['text'=>"💳 CC/Visa Gate",'callback_data'=>"checkergates"]],[['text'=>"🛠 Other",'callback_data'=>"othercmds"]]])]);

// Module Router
if(strpos($message,"/visa ")===0 || strpos($message,"!visa ")===0) require __DIR__."/modules/checker/visa.php";
elseif(strpos($message,"/ss ")===0 || strpos($message,"!ss ")===0) require __DIR__."/modules/checker/ss.php";
elseif(strpos($message,"/sm ")===0 || strpos($message,"!sm ")===0) require __DIR__."/modules/checker/sm.php";
elseif(strpos($message,"/schk ")===0 || strpos($message,"!schk ")===0) require __DIR__."/modules/checker/schk.php";
elseif(strpos($message,"/me ")===0 || strpos($message,"!me ")===0) require __DIR__."/modules/me.php";
elseif(strpos($message,"/stats ")===0 || strpos($message,"!stats ")===0) require __DIR__."/modules/stats.php";
elseif(strpos($message,"/bin ")===0 || strpos($message,"!bin ")===0) require __DIR__."/modules/binlookup.php";
elseif(strpos($message,"/iban ")===0) require __DIR__."/modules/iban.php";
elseif(strpos($message,"/key ")===0 || strpos($message,"!key ")===0) require __DIR__."/modules/skcheck.php";
elseif(strpos($message,"/apikey ")===0) require __DIR__."/modules/apikey.php";
elseif($userId == $config['adminID'] && (strpos($message,"/admin ")===0 || strpos($message,"/mute ")===0 || strpos($message,"/unmute ")===0 || strpos($message,"/ban ")===0)) require __DIR__."/modules/admin.php";
?>
