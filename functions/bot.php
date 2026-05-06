<?php
function bot($method,$datas=[]){
    global $config;
    $ch = curl_init("https://api.telegram.org/bot{$config['botToken']}/$method");
    curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);
    curl_setopt($ch,CURLOPT_POSTFIELDS,$datas);
    $res = curl_exec($ch);
    if(curl_error($ch)) var_dump(curl_error($ch));
    else return json_decode($res);
}
?>
