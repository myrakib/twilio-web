from flask import Flask, request, jsonify, render_template_string, session
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "change_this_secret"

# ---------------- HTML (FRONTEND) ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Twilio Web Panel</title>
<style>
body { font-family: Arial; background:#1e1e2f; color:white; margin:0; padding:20px; }
.box { background:#2a2a40; padding:15px; margin-bottom:15px; border-radius:10px; }
input, select { padding:8px; margin:5px; width:250px; }
button { padding:8px 12px; margin:5px; cursor:pointer; }
ul { list-style:none; padding:0; }
li { padding:5px; margin:5px 0; background:#3a3a55; border-radius:5px; }
pre { background:#3a3a55; padding:10px; border-radius:5px; }
</style>
</head>
<body>

<h2>📞 Twilio Web Panel</h2>

<div class="box">
<h3>Login</h3>
<input id="sid" placeholder="Account SID"><br>
<input id="token" placeholder="Auth Token"><br>
<button onclick="login()">Login</button>
</div>

<div class="box">
<h3>Search Numbers</h3>
<select id="country">
<option>US</option>
<option>CA</option>
<option>PR</option>
</select>
<button onclick="searchNumbers()">Search</button>
<ul id="numbers"></ul>
</div>

<div class="box">
<h3>My Numbers</h3>
<button onclick="loadMyNumbers()">Refresh</button>
<ul id="myNumbers"></ul>
</div>

<div class="box">
<h3>Messages</h3>
<button onclick="loadMessages()">Load</button>
<pre id="msgs"></pre>
</div>

<script>
async function login(){
    await fetch("/login", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            sid: document.getElementById("sid").value,
            token: document.getElementById("token").value
        })
    });
    alert("Logged in");
}

async function searchNumbers(){
    let country = document.getElementById("country").value;
    let res = await fetch("/search_numbers?country=" + country);
    let data = await res.json();

    let list = document.getElementById("numbers");
    list.innerHTML = "";

    data.forEach(num=>{
        let li = document.createElement("li");
        li.innerHTML = num + " <button onclick='buy(\""+num+"\")'>Buy</button>";
        list.appendChild(li);
    });
}

async function buy(num){
    await fetch("/buy_number", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({number:num})
    });
    alert("Purchased!");
}

async function loadMyNumbers(){
    let res = await fetch("/my_numbers");
    let data = await res.json();

    let list = document.getElementById("myNumbers");
    list.innerHTML = "";

    data.forEach(n=>{
        let li = document.createElement("li");
        li.textContent = n.number;
        list.appendChild(li);
    });
}

async function loadMessages(){
    let res = await fetch("/messages");
    let data = await res.json();

    document.getElementById("msgs").textContent =
        data.map(m => `From: ${m.from}\n${m.body}\n---`).join("\n");
}
</script>

</body>
</html>
"""

# ---------------- TWILIO CLIENT ----------------
def get_client():
    sid = session.get("sid")
    token = session.get("token")
    if not sid or not token:
        return None
    return Client(sid, token)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    session["sid"] = data["sid"]
    session["token"] = data["token"]
    return jsonify({"status": "ok"})

@app.route("/search_numbers")
def search_numbers():
    client = get_client()
    if not client:
        return jsonify([])

    country = request.args.get("country", "US")
    numbers = client.available_phone_numbers(country).local.list(limit=10)

    return jsonify([n.phone_number for n in numbers])

@app.route("/buy_number", methods=["POST"])
def buy_number():
    client = get_client()
    if not client:
        return jsonify({"error": "not logged in"})

    number = request.json["number"]
    client.incoming_phone_numbers.create(phone_number=number)

    return jsonify({"status": "purchased"})

@app.route("/my_numbers")
def my_numbers():
    client = get_client()
    if not client:
        return jsonify([])

    nums = client.incoming_phone_numbers.list()

    return jsonify([
        {"number": n.phone_number}
        for n in nums
    ])

@app.route("/messages")
def messages():
    client = get_client()
    if not client:
        return jsonify([])

    msgs = client.messages.list(limit=20)

    return jsonify([
        {"from": m.from_, "body": m.body}
        for m in reversed(msgs)
    ])

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
