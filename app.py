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
    return dt.replace(tzinfo=timezone.utc).astimezone(BD_TZ).strftime("%d-%m %I:%M")


HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Phone Panel</title>

<style>
body{
    font-size:18px;
    font-family:Arial;
    background:#f4f4f4;
    margin:0;
    padding:20px;
}

.top-left{
    position:fixed;
    top:10px;
    left:10px;
    background:white;
    padding:10px;
    border-radius:8px;
    width:220px;
    box-shadow:0 0 10px #ccc;
    font-size:16px;
}

button{
    font-size:16px;
    padding:8px 12px;
    margin:4px;
}

.green{background:#28a745;color:white;border:none;}
.blue{background:#007bff;color:white;border:none;}
.red{background:#dc3545;color:white;border:none;}

.section{
    margin-top:15px;
}

.sms{
    background:white;
    padding:6px 8px;
    margin:4px 0;
    border-left:4px solid #007bff;
    font-size:14px;
}

.search-box{
    background:white;
    padding:10px;
    border-radius:8px;
    margin:8px 0;
}

/* FOOTER */
.footer{
    position:fixed;
    bottom:10px;
    right:10px;
    font-size:14px;
    color:gray;
    background:white;
    padding:6px 10px;
    border-radius:6px;
    box-shadow:0 0 8px #ccc;
}
</style>

</head>

<body>

<!-- LEFT NUMBERS -->
<div class="top-left">
<b>Your Numbers</b><br>
{% for n in numbers %}
<div>
{{ n }}
<form method="POST" style="display:inline;">
<input type="hidden" name="number" value="{{ n }}">
<button class="red" name="action" value="delete">X</button>
</form>
</div>
{% endfor %}
</div>

<h2>📱 Dashboard</h2>

{% if not session.get('logged_in') %}

<form method="POST">
<input name="sid" placeholder="SID">
<input name="token" placeholder="TOKEN">
<button class="green" name="action" value="login">Login</button>
</form>

{% else %}

<!-- BUY SECTION -->
<div class="section">
<h3>🛒 Buy Numbers</h3>

<form method="POST">
<input name="area" placeholder="Area code optional">
<button class="green" name="action" value="search">Search CA Numbers</button>
</form>

<form method="POST">
<button class="blue" name="action" value="buy_random">Buy Random CA (5)</button>
</form>
</div>

<!-- SMS SECTION -->
<div class="section">
<h3>📩 Incoming SMS</h3>

<form method="POST">
<button class="blue" name="action" value="sms">Refresh SMS</button>
</form>

{% for m in sms_inbox %}
<div class="sms">
<b>{{ m.from }}</b> - {{ m.body }}
<br>
<small>{{ m.time }}</small>
</div>
{% endfor %}
</div>

<!-- SEARCH RESULTS -->
<div class="section">
<h3>🔎 Available Numbers (CA)</h3>

{% for n in search_results %}
<div class="search-box">
{{ n }}
<form method="POST">
<input type="hidden" name="number" value="{{ n }}">
<button class="blue" name="action" value="buy">Buy</button>
</form>
</div>
{% endfor %}
</div>

<hr>

<form method="POST">
<button class="red" name="action" value="logout">Logout</button>
</form>

<!-- FOOTER -->
<div class="footer">
Created by Rakibul Islam
</div>

{% endif %}

</body>
</html>
"""


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


@app.route("/", methods=["GET", "POST"])
def index():
    global client, numbers_cache, search_results, sms_inbox

    action = request.form.get("action")

    if action == "login":
        client = Client(request.form["sid"], request.form["token"])
        session["logged_in"] = True
        refresh_numbers()

    elif action == "logout":
        client = None
        numbers_cache = []
        search_results = []
        sms_inbox = []
        session.clear()

    elif action == "search":
        search_results = generate_fake_numbers(request.form.get("area"))

    elif action == "buy_random":
        search_results = generate_fake_numbers()

    elif action == "buy" and client:
        client.incoming_phone_numbers.create(phone_number=request.form["number"])
        refresh_numbers()

    elif action == "delete" and client:
        num = request.form["number"]
        for n in client.incoming_phone_numbers.list():
            if n.phone_number == num:
                client.incoming_phone_numbers(n.sid).delete()
        refresh_numbers()

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

    return render_template_string(
        HTML,
        numbers=numbers_cache,
        search_results=search_results,
        sms_inbox=sms_inbox
    )


if __name__ == "__main__":
    app.run(debug=True)
