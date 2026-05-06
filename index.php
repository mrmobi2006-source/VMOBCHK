<?php
header("Content-Type: application/json");
if($_SERVER['REQUEST_METHOD'] === 'POST') {
    require __DIR__ . "/main.php";
} else {
    echo json_encode(["status" => "running", "bot" => "online"]);
}
?>
