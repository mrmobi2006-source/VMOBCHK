<?php
require __DIR__ . "/../../config/config.php";
require __DIR__ . "/../../config/variables.php";
require_once __DIR__ . "/../../functions/bot.php";
require_once __DIR__ . "/../../functions/db.php";
require_once __DIR__ . "/../../functions/functions.php";

if(strpos($message, "/visa ")===0 || strpos($message, "!visa ")===0){
    if(antispamCheck($userId)){ bot('sendmessage',['chat_id'=>$chat_id,'text'=>"[<u>ANTI SPAM</u>] Wait <b>".antispamCheck($userId)."</b>s."]); return; }
    $m = bot('sendmessage',['chat_id'=>$chat_id,'text'=>"⏳ Checking Visa Status..."]);
    $mid = $m->message_id;
    $raw = trim(substr($message, 6));
    $parts = explode(" ", $raw);
    $country = strtolower($parts[0]); $app = $parts[1];
    
    $res = "❌ Invalid Format. Use: /visa [country] [APP_ID]";
    if(in_array($country,['us','uk','schengen']) && strlen($app)>4){
        // Simulates official CEAC/UKVI API hit with proper UA/Cookies
        $ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";
        $ch = curl_init("https://ceac.state.gov/CEAC/Status/Check"); // Mock/Real structure
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_USERAGENT, $ua);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ["Content-Type: application/json", "Accept: application/json"]);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['caseNumber'=>$app, 'country'=>$country]));
        $r = curl_exec($ch); $time = round(curl_getinfo($ch, CURLINFO_TOTAL_TIME), 2);
        curl_close($ch);
        
        $status = json_decode($r, true);
        if(isset($status['status'])){
            $st = strtoupper($status['status']); $em = ($st=='ISSUED'||$st=='APPROVED')?'✅':'🟡';
            $res = "<b>🌍 Visa Status Check</b>\n<b>Country:</b> $country\n<b>App ID:</b> <code>$app</code>\n<b>Status:</b> $em $st\n<b>Response:</b> ".($status['details']?''.htmlspecialchars($status['details']).'':'Pending Admin Review')."\n<b>Time:</b> {$time}s\n━━━━━━━━━━━━━\n<b>Checked By: <a href='tg://user?id=$userId'>$firstname</a></b>";
        } else { $res = "<b>❌ App Not Found / API Down</b>"; }
    }
    bot('editMessageText',['chat_id'=>$chat_id,'message_id'=>$mid,'text'=>$res,'parse_mode'=>'html']);
}
?>
