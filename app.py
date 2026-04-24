from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "change_this_secret"

# ---------------- HTML TEMPLATE ----------------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Twilio Web Dashboard</title>
    <style>
        body {
            font-family: Arial;
            margin: 20px;
            background: #fff0f6;
            color: #333;
        }

        h2 {
            color: #d63384;
        }

        .box {
            padding: 15px;
            border: 2px solid #f8bbd0;
            background: white;
            border-radius: 12px;
            margin-bottom: 18px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }

        button {
            margin-top: 8px;
            padding: 8px 14px;
            border: none;
            border-radius: 8px;
            background: #ff4da6;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background: #e60073;
        }

        input, select {
            padding: 8px;
            margin-top: 6px;
            margin-bottom: 8px;
            border: 1px solid #f8bbd0;
            border-radius: 8px;
            width: 320px;
        }

        .delete-btn {
            background: #ff5c8a;
        }

        .delete-btn:hover {
            background: #d6336c;
        }

        pre {
            white-space: pre-wrap;
            background: #fff8fb;
            padding: 10px;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <h2>🌸 Twilio Pink Dashboard</h2>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for message in messages %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    <div class="box">
        <h3>Login</h3>
        <form method="POST" action="/login">
            <input name="sid" placeholder="Account SID" required><br>
            <input name="token" placeholder="Auth Token" type="password" required><br>
            <button type="submit">Login</button>
        </form>
        <br>
        <a href="/logout">Logout</a>
    </div>

    {% if session.get('logged_in') %}

    <div class="box">
        <h3>Search Numbers</h3>
        <form method="POST" action="/search">
            <select name="country">
                <option>US</option>
                <option>CA</option>
                <option>PR</option>
            </select><br>
            <button type="submit">Search</button>
        </form>

        {% if numbers %}
            <form method="POST" action="/buy">
                {% for n in numbers %}
                    <input type="radio" name="number" value="{{n}}"> {{n}}<br>
                {% endfor %}
                <button type="submit">Buy Selected Number</button>
            </form>
        {% endif %}
    </div>

    <div class="box">
        <h3>Manual Number Buy</h3>
        <form method="POST" action="/buy-manual">
            <input name="manual_number" placeholder="Enter phone number manually (example: +1234567890)" required><br>
            <button type="submit">Buy Manual Number</button>
        </form>
    </div>

    <div class="box">
        <h3>Current Numbers</h3>
        <a href="/my-numbers">Refresh Current Numbers</a>
        <ul>
        {% for n in my_numbers %}
            <li>
                {{n.phone}}<br>
                SID: {{n.sid}}
                <form method="POST" action="/delete" style="margin-top:8px;">
                    <input type="hidden" name="sid" value="{{n.sid}}">
                    <button class="delete-btn" type="submit">Delete Number</button>
                </form>
            </li>
            <hr>
        {% endfor %}
        </ul>
    </div>

    <div class="box">
        <h3>Messages</h3>
        <a href="/messages">Refresh Messages</a>
        <pre>{{messages}}</pre>
    </div>

    {% endif %}
</body>
</html>
"""

# ---------------- GLOBAL ----------------
client = None
numbers_cache = []


# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template_string(TEMPLATE, numbers=numbers_cache, my_numbers=[], messages="")


@app.route('/login', methods=['POST'])
def login():
    global client

    sid = request.form['sid']
    token = request.form['token']

    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        session['logged_in'] = True
        flash("Logged in successfully")
    except Exception as e:
        flash(str(e))

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    global client
    client = None
    session.clear()
    flash("Logged out")
    return redirect(url_for('index'))


@app.route('/search', methods=['POST'])
def search():
    global numbers_cache

    if not client:
        return redirect(url_for('index'))

    country = request.form['country']

    try:
        nums = client.available_phone_numbers(country).local.list(limit=10)
        numbers_cache = [n.phone_number for n in nums]
    except Exception as e:
        flash(str(e))

    return redirect(url_for('index'))


@app.route('/buy', methods=['POST'])
def buy():
    if not client:
        return redirect(url_for('index'))

    number = request.form.get('number')

    try:
        client.incoming_phone_numbers.create(phone_number=number)
        flash(f"Bought {number}")
    except Exception as e:
        flash(str(e))

    return redirect(url_for('index'))


@app.route('/buy-manual', methods=['POST'])
def buy_manual():
    if not client:
        return redirect(url_for('index'))

    number = request.form.get('manual_number')

    try:
        client.incoming_phone_numbers.create(phone_number=number)
        flash(f"Manual number bought: {number}")
    except Exception as e:
        flash(str(e))

    return redirect(url_for('index'))


@app.route('/delete', methods=['POST'])
def delete_number():
    if not client:
        return redirect(url_for('index'))

    sid = request.form.get('sid')

    try:
        client.incoming_phone_numbers(sid).delete()
        flash("Number deleted successfully")
    except Exception as e:
        flash(str(e))

    return redirect(url_for('my_numbers'))


@app.route('/my-numbers')
def my_numbers():
    if not client:
        return redirect(url_for('index'))

    nums = client.incoming_phone_numbers.list()
    data = [{"sid": n.sid, "phone": n.phone_number} for n in nums]

    return render_template_string(
        TEMPLATE,
        numbers=numbers_cache,
        my_numbers=data,
        messages=""
    )


@app.route('/messages')
def messages():
    if not client:
        return redirect(url_for('index'))

    msgs = client.messages.list(limit=20)
    text = "\n".join([
        f"From: {m.from_}\n{m.body}\n---"
        for m in msgs
    ])

    return render_template_string(
        TEMPLATE,
        numbers=numbers_cache,
        my_numbers=[],
        messages=text
    )


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
