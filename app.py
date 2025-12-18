from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

rooms = {}


@app.route("/")
def index():
    return """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Лобби — REST чат</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 20px auto; }
        #roomInfo { margin-top: 10px; }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Лобби</h1>

<div>
    <button id="createBtn">Создать комнату</button>
</div>

<div style="margin-top: 10px;">
    <input id="joinInput" placeholder="ID комнаты для подключения">
    <button id="joinBtn">Подключиться</button>
</div>

<script>
function createRoom() {
    fetch("/create_room", { method: "POST" })
        .then(r => r.json())
        .then(data => {
            const id = data.room_id;
            console.log("ID созданной комнаты:", id);
            window.location.href = "/chat?room_id=" + encodeURIComponent(id);
        });
}

function joinRoom() {
    const id = document.getElementById("joinInput").value.trim();
    if (!id) {
        alert("Введите ID комнаты");
        return;
    }
    fetch("/join_room", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({room_id: id})
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            window.location.href = "/chat?room_id=" + encodeURIComponent(id);
        });
}

document.getElementById("createBtn").addEventListener("click", createRoom);
document.getElementById("joinBtn").addEventListener("click", joinRoom);
</script>
</body>
</html>
"""

@app.route("/chat")
def chat_page():
    return """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Чат — REST чат</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 20px auto; }
        #chat { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 5px; margin-top: 10px; }
        #roomInfo { margin-top: 10px; }
        .msg-author { font-weight: bold; }
        .msg-line { margin: 2px 0; }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Комната</h1>

<div id="roomInfo">
    Текущая комната: <span id="currentRoom">нет</span>
</div>

<div style="margin-top: 10px;">
    <input id="nameInput" placeholder="Ваше имя" value="user1">
</div>

<div id="chat"></div>

<div style="margin-top: 10px;">
    <input id="msgInput" style="width: 80%;" placeholder="Сообщение">
    <button id="sendBtn">Отправить</button>
</div>

<script>
let currentRoomId = null;
let lastIndex = 0;
let pollTimer = null;

function appendMessage(author, text) {
    const chat = document.getElementById("chat");
    const line = document.createElement("div");
    line.className = "msg-line";
    const authorSpan = document.createElement("span");
    authorSpan.className = "msg-author";
    authorSpan.textContent = author + ": ";
    const textSpan = document.createElement("span");
    textSpan.textContent = text;
    line.appendChild(authorSpan);
    line.appendChild(textSpan);
    chat.appendChild(line);
    chat.scrollTop = chat.scrollHeight;
}

function startPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
    }
    pollTimer = setInterval(fetchMessages, 1000);
}

function initRoom() {
    const params = new URLSearchParams(window.location.search);
    currentRoomId = params.get("room_id");
    if (!currentRoomId) {
        alert("room_id не передан");
        return;
    }
    console.log("ID комнаты:", currentRoomId);
    document.getElementById("currentRoom").textContent = currentRoomId;
    fetch("/join_room", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({room_id: currentRoomId})
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            lastIndex = 0;
            document.getElementById("chat").innerHTML = "";
            startPolling();
        });
}

function sendMessage() {
    if (!currentRoomId) {
        alert("Комната не выбрана");
        return;
    }
    const name = document.getElementById("nameInput").value.trim() || "anon";
    const text = document.getElementById("msgInput").value.trim();
    if (!text) {
        return;
    }
    fetch("/send_message", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({room_id: currentRoomId, author: name, text: text})
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            document.getElementById("msgInput").value = "";
        });
}

function fetchMessages() {
    if (!currentRoomId) return;
    fetch("/get_messages?room_id=" + encodeURIComponent(currentRoomId) + "&after=" + lastIndex)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                console.log("Ошибка получения сообщений:", data.error);
                return;
            }
            const msgs = data.messages || [];
            for (const m of msgs) {
                appendMessage(m.author, m.text);
            }
            lastIndex = data.next_index;
        });
}

document.getElementById("sendBtn").addEventListener("click", sendMessage);
document.getElementById("msgInput").addEventListener("keydown", function(e) {
    if (e.key === "Enter") sendMessage();
});
initRoom();
</script>
</body>
</html>
"""


@app.post("/create_room")
def create_room():
    room_id = uuid.uuid4().hex[:6]
    rooms[room_id] = []
    return jsonify({"room_id": room_id})


@app.post("/join_room")
def join_room():
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    if not room_id or room_id not in rooms:
        return jsonify({"error": "Комната не найдена"}), 404
    return jsonify({"ok": True, "room_id": room_id})


@app.post("/send_message")
def send_message():
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    author = data.get("author") or "anon"
    text = data.get("text") or ""
    if not room_id or room_id not in rooms:
        return jsonify({"error": "Комната не найдена"}), 404
    if not text:
        return jsonify({"error": "Пустое сообщение"}), 400
    message = {"author": author, "text": text}
    rooms[room_id].append(message)
    return jsonify({"ok": True})


@app.get("/get_messages")
def get_messages():
    room_id = request.args.get("room_id")
    if not room_id or room_id not in rooms:
        return jsonify({"error": "Комната не найдена"}), 404
    try:
        after = int(request.args.get("after", "0"))
    except ValueError:
        after = 0
    messages = rooms[room_id]
    new_messages = messages[after:]
    return jsonify({"messages": new_messages, "next_index": len(messages)})


if __name__ == "__main__":
    app.run(debug=True)

