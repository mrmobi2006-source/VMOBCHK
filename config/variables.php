<?php
$update = json_decode(file_get_contents("php://input"));
if (!$update) exit;
$chat_id       = $update->message->chat->id ?? null;
$userId        = $update->message->from->id ?? null;
$firstname     = $update->message->from->first_name ?? '';
$lastname      = $update->message->from->last_name ?? '';
$username      = $update->message->from->username ?? '';
$chattype      = $update->message->chat->type ?? 'private';
$message       = $update->message->text ?? '';
$message_id    = $update->message->message_id ?? null;
$data          = $update->callback_query->data ?? '';
$callbackfname = $update->callback_query->from->first_name ?? '';
$callbacklname = $update->callback_query->from->last_name ?? '';
$callbackusername = $update->callback_query->from->username ?? '';
$callbackchatid   = $update->callback_query->message->chat->id ?? '';
$callbackuserid   = $update->callback_query->message->reply_to_message->from->id ?? '';
$callbackmessageid= $update->callback_query->message->message_id ?? '';
$live_array = ['incorrect_cvc','"cvc_check":"fail"','"cvc_check":"pass"','insufficient_funds','transaction_not_allowed','CVV INVALID'];
?>
