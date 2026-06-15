from flask import Flask, render_template_string, request, session
from twilio.rest import Client
from datetime import timezone, timedelta
import random

app = Flask(__name__)
app.secret_key = "change_this_secret"

client = None
numbers_cache = []
search_results = []
sms_inbox = []

BD_TZ = timezone(timedelta(hours=6))


def to_bd_time(dt):
    if not dt:
        return "Unknown"
    return dt.astimezone(BD_TZ).strftime("%d-%m %I:%M %p")


# ---------------- UI ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Twilio Dashboard</title>

<style>
body { font-family: Arial; background:#0f172a; color:white; margin:0; }
.container { padding:20px; max-width:1000px; margin:auto; }

.card { background:#1e293b; padding:15px; margin:10px 0; border-radius:10px; }

input { padding:10px; width:200px; margin:5px; border-radius:5px; border:none; }

button {
    padding:10px 15px;
    border:none;
    border-radius:5px;
    cursor:pointer;
    margin:5px;
}

.login-btn { background:#22c55e; color:white; }
.buy-btn { background:#3b82f6; color:white; }
.search-btn { background:#f59e0b; color:black; }
.delete-btn { background:#ef4444; color:white; }
.sms-btn { background:#8b5cf6; color:white; }

.number-box {
    display:flex;
    justify-content:space-between;
    padding:8px;
    background:#334155;
    margin:5px 0;
    border-radius:6px;
}

h2,h3 { margin:10px 0; }
</style>

</head>

<body>
<div class="container">

<h2>📡 Twilio Control Panel</h2>

{% if not session.get('logged_in') %}

<div class="card">
<h3>🔐 Login</h3>
<form method="POST">
<input name="sid" placeholder="SID">
<input name="token" placeholder="Token">
<button class="login-btn" name="action" value="login">Login</button>
</form>
</div>

{% else %}

<form method="POST">
<button class="delete-btn" name="action" value="logout">Logout</button>
</form>

<!-- SEARCH -->
<div class="card">
<h3>🔎 Search Numbers (Area Code)</h3>
<form method="POST">
<input name="area" placeholder="Enter Area Code">
<button class="search-btn" name="action" value="search">Search</button>
</form>

{% for n in search_results %}
<div class="number-box">
<span>{{ n }}</span>
<form method="POST">
<input type="hidden" name="number" value="{{ n }}">
<button class="buy-btn" name="action" value="buy">Buy</button>
</form>
</div>
{% endfor %}
</div>

<!-- SMS -->
<div class="card">
<h3>📩 Incoming SMS</h3>
<form method="POST">
<button class="sms-btn" name="action" value="sms">Load SMS</button>
</form>

{% for m in sms_inbox %}
<div class="card">
<b>From:</b> {{ m.from }} <br>
<b>Msg:</b> {{ m.body }} <br>
<b>Time:</b> {{ m.time }}
</div>
{% endfor %}
</div>

<!-- NUMBERS -->
<div class="card">
<h3>📱 Your Numbers</h3>

{% for n in numbers %}
<div class="number-box">
<span>{{ n }}</span>
<form method="POST">
<input type="hidden" name="number" value="{{ n }}">
<button class="delete-btn" name="action" value="delete">Delete</button>
</form>
</div>
{% endfor %}

</div>

{% endif %}

</div>
</body>
</html>
"""


# ---------------- HELPERS ----------------
def refresh_numbers():
    global numbers_cache
    if client:
        numbers_cache = [n.phone_number for n in client.incoming_phone_numbers.list()]


def generate_fake_numbers(area=None):
    base = "+1"
    return [
        f"{base}{area if area else random.randint(200,999)}{random.randint(1000000,9999999)}"
        for _ in range(5)
    ]


# ---------------- ROUTE ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    global client, search_results, sms_inbox

    action = request.form.get("action")

    # LOGIN
    if action == "login":
        client = Client(request.form["sid"], request.form["token"])
        session["logged_in"] = True
        refresh_numbers()

    # LOGOUT
    elif action == "logout":
        client = None
        search_results = []
        sms_inbox = []
        session.clear()

    # SEARCH NUMBERS
    elif action == "search":
        search_results = generate_fake_numbers(request.form.get("area"))

    # BUY NUMBER (FIXED FLOW)
    elif action == "buy" and client:
        number = request.form["number"]

        available = client.available_phone_numbers("US").local.list(limit=1)
        if available:
            client.incoming_phone_numbers.create(
                phone_number=available[0].phone_number
            )
            refresh_numbers()

    # SMS INBOX
    elif action == "sms" and client:
        sms_inbox = []
        msgs = client.messages.list(limit=20)

        for m in msgs:
            if m.direction == "inbound":
                sms_inbox.append({
                    "from": m.from_,
                    "body": m.body,
                    "time": to_bd_time(m.date_sent)
                })

    # DELETE NUMBER
    elif action == "delete" and client:
        num = request.form["number"]
        for n in client.incoming_phone_numbers.list():
            if n.phone_number == num:
                client.incoming_phone_numbers(n.sid).delete()
        refresh_numbers()

    return render_template_string(
        HTML,
        numbers=numbers_cache,
        search_results=search_results,
        sms_inbox=sms_inbox
    )


if __name__ == "__main__":
    app.run(debug=True)
