<?php
require __DIR__ . "/../config/config.php";
$port = isset($config['db']['port']) ? $config['db']['port'] : 3306;
$conn = mysqli_connect($config['db']['hostname'], $config['db']['username'], $config['db']['password'], $config['db']['database'], $port);
if (!$conn) {
    error_log("DB Connection Failed: " . mysqli_connect_error());
    die("DB Error");
}

function fetchUser($userID){ global $conn; $r = mysqli_query($conn,"SELECT * FROM users WHERE userid='$userID'"); return mysqli_num_rows($r) ? $r->fetch_assoc() : false; }
function isBanned($userID){ global $chat_id, $message_id; $d = fetchUser($userID); return ($d && $d['is_banned']=="True") ? true : false; }
function isMuted($userID){ global $conn, $chat_id, $message_id; $d = fetchUser($userID); if($d && $d['is_muted']=="True"){ if($d['mute_timer']>time()){ bot('sendmessage',['chat_id'=>$chat_id,'text'=>'<b>🛑 Muted until '.date("Y-m-d H:i",$d['mute_timer']).'</b>','parse_mode'=>'html','reply_to_message_id'=>$message_id]); return true;} else { mysqli_query($conn,"UPDATE users SET is_muted='False',mute_timer='0' WHERE userid='$userID'"); return false; } } return false; }
function addUser($userID){ global $conn; if(!fetchUser($userID)){ mysqli_query($conn,"INSERT INTO users (userid,registered_on,is_banned,is_muted,mute_timer,sk_key,total_checked,total_cvv,total_ccn) VALUES ('$userID',UNIX_TIMESTAMP(),'False','False','0','','0','0','0')"); return true; } return false; }
function muteUser($uid,$t){ global $conn; if(fetchUser($uid)){ mysqli_query($conn,"UPDATE users SET is_muted='True',mute_timer='$t' WHERE userid='$uid'"); return "Muted $uid until ".date("Y-m-d H:i",$t); } return "User not found"; }
function unmuteUser($uid){ global $conn; mysqli_query($conn,"UPDATE users SET is_muted='False',mute_timer='0' WHERE userid='$uid'"); return "Unmuted $uid"; }
function banUser($uid){ global $conn; if(fetchUser($uid)){ mysqli_query($conn,"UPDATE users SET is_banned='True' WHERE userid='$uid'"); return "Banned $uid"; } return "User not found"; }
function unbanUser($uid){ global $conn; mysqli_query($conn,"UPDATE users SET is_banned='False' WHERE userid='$uid'"); return "Unbanned $uid"; }
function fetchMutelist(){ global $conn; $r = mysqli_query($conn,"SELECT userid FROM users WHERE is_muted='True'"); return $r->num_rows ? $r->fetch_assoc() : false; }
function fetchBanlist(){ global $conn; $r = mysqli_query($conn,"SELECT userid FROM users WHERE is_banned='True'"); return $r->num_rows ? $r->fetch_assoc() : false; }
function totalBanned(){ global $conn; return mysqli_num_rows(mysqli_query($conn,"SELECT * FROM users WHERE is_banned='True'")); }
function totalMuted(){ global $conn; return mysqli_num_rows(mysqli_query($conn,"SELECT * FROM users WHERE is_muted='True'")); }
function antispamCheck($uid){ global $conn, $config; if($uid==$config['adminID']) return false; $r = mysqli_query($conn,"SELECT * FROM antispam WHERE userid='$uid'"); if($r->num_rows){ $d=$r->fetch_assoc(); if(time()-$d['last_checked_on']>$config['anti_spam_timer']){ mysqli_query($conn,"UPDATE antispam SET last_checked_on='".time()."' WHERE userid='$uid'"); return false;} else { return $config['anti_spam_timer']-(time()-$d['last_checked_on']); } } else { mysqli_query($conn,"INSERT INTO antispam (userid,last_checked_on) VALUES ('$uid','".time()."')"); return false; } }
function fetchGlobalStats(){ global $conn; return mysqli_query($conn,"SELECT * FROM global_checker_stats")->fetch_assoc(); }
function addTotal(){ global $conn; mysqli_query($conn,"UPDATE global_checker_stats SET total_checked=total_checked+1"); }
function addCVV(){ global $conn; mysqli_query($conn,"UPDATE global_checker_stats SET total_cvv=total_cvv+1"); }
function addCCN(){ global $conn; mysqli_query($conn,"UPDATE global_checker_stats SET total_ccn=total_ccn+1"); }
function fetchUserStats($uid){ global $conn; return mysqli_query($conn,"SELECT total_checked,total_cvv,total_ccn FROM users WHERE userid='$uid'")->fetch_assoc(); }
function addUserTotal($uid){ global $conn; mysqli_query($conn,"UPDATE users SET total_checked=total_checked+1 WHERE userid='$uid'"); }
function addUserCVV($uid){ global $conn; mysqli_query($conn,"UPDATE users SET total_cvv=total_cvv+1 WHERE userid='$uid'"); }
function addUserCCN($uid){ global $conn; mysqli_query($conn,"UPDATE users SET total_ccn=total_ccn+1 WHERE userid='$uid'"); }
function fetchAPIKey($uid){ global $conn; $r = mysqli_query($conn,"SELECT sk_key FROM users WHERE userid='$uid'"); return $r->num_rows ? $r->fetch_assoc()['sk_key'] : ''; }
function updateAPIKey($uid,$k){ global $conn; mysqli_query($conn,"UPDATE users SET sk_key='$k' WHERE userid='$uid'"); }
?>
