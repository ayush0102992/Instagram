from flask import Flask, request, render_template_string, jsonify, session, redirect
import requests
from threading import Thread, Event
import time
import random
import string
from datetime import datetime
import secrets
import json
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# DATA STORAGE (File-based for Render)
USERS_FILE = 'users.json'
THREADS_FILE = 'threads.json'

def load_data(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

users = load_data(USERS_FILE)  # gmail: {"password": "hash", "user_id": "..."}
threads = {}          # thread_id: thread
stop_events = {}      # thread_id: Event
tasks = {}            # thread_id: task
counters = {}         # thread_id: counters
logs = {}             # thread_id: logs
user_threads = {}     # user_id -> [thread_ids]
thread_details = {}   # thread_id -> details

# Token Checker
def check_token_validity(token):
    url = "https://graph.facebook.com/v15.0/me"
    params = {'access_token': token, 'fields': 'name'}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            name = r.json().get('name', 'Unknown')
            return {"valid": True, "name": name, "expiry": 58}
        else:
            return {"valid": False, "name": "Invalid", "expiry": 0}
    except:
        return {"valid": False, "name": "Error", "expiry": 0}

# Generate Task
def generate_task():
    t = random.choice(["math", "captcha", "reverse"])
    if t == "math":
        a, b = random.randint(1, 15), random.randint(1, 15)
        return {"question": f"{a} + {b} = ?", "answer": str(a + b)}
    elif t == "captcha":
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        return {"question": f"Type: <code>{code}</code>", "answer": code}
    elif t == "reverse":
        word = random.choice(["LEGEND", "ERROR", "BOI", "FIRE", "STOP"])
        return {"question": f"Reverse: <b>{word}</b>", "answer": word[::-1]}

# Send Messages
def send_messages(thread_id, access_tokens, convo_id, hater_name, delay, messages):
    stop_event = stop_events[thread_id]
    sent = failed = 0
    logs[thread_id] = []

    valid_tokens = []
    for token in access_tokens:
        info = check_token_validity(token)
        if info["valid"]:
            valid_tokens.append(token)
        else:
            logs[thread_id].append(f"<span style='color:#f55'>[INVALID] {token[:20]}...</span>")

    if not valid_tokens:
        logs[thread_id].append("<span style='color:#ff0'>[STOP] No valid tokens!</span>")
        return

    while not stop_event.is_set():
        for msg in messages:
            if stop_event.is_set(): break
            token = random.choice(valid_tokens)
            url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
            full_msg = f"{hater_name} {msg.strip()}"
            params = {'access_token': token, 'message': full_msg}

            try:
                r = requests.post(url, data=params, timeout=10)
                ts = datetime.now().strftime("%H:%M:%S")
                if r.status_code == 200:
                    log = f"<span style='color:#0f0'>[{ts}] SENT: {full_msg}</span>"
                    sent += 1
                else:
                    log = f"<span style='color:#f55'>[{ts}] FAIL: {r.status_code}</span>"
                    failed += 1
            except:
                log = f"<span style='color:#ff0'>[{ts}] ERR: network</span>"
                failed += 1

            logs[thread_id].append(log)
            if len(logs[thread_id]) > 200:
                logs[thread_id] = logs[thread_id][-200:]
            counters[thread_id] = {"sent": sent, "failed": failed}
            time.sleep(delay)

    # Cleanup
    for d in [threads, stop_events, tasks, counters, logs, thread_details]:
        d.pop(thread_id, None)
    save_data(THREADS_FILE, thread_details)

# LOGIN / REGISTER PAGE
@app.route('/', methods=['GET', 'POST'])
def login_register():
    if request.method == 'POST':
        action = request.form.get('action')
        gmail = request.form.get('gmail', '').strip().lower()
        password = request.form.get('password', '').strip()

        if action == 'register':
            if gmail in users:
                return "<p style='color:#f55;'>Gmail already registered!</p>" + LOGIN_FORM
            users[gmail] = {
                "password": password,  # Plain text (Render pe safe hai)
                "user_id": secrets.token_hex(8)
            }
            if users[gmail]["user_id"] not in user_threads:
                user_threads[users[gmail]["user_id"]] = []
            save_data(USERS_FILE, users)
            return "<p style='color:#0f0;'>Registered! Now login.</p>" + LOGIN_FORM

        elif action == 'login':
            if gmail in users and users[gmail]["password"] == password:
                session['user_id'] = users[gmail]["user_id"]
                session['gmail'] = gmail
                return redirect('/dashboard')
            else:
                return "<p style='color:#f55;'>Wrong Gmail/Password!</p>" + LOGIN_FORM

        # ADMIN LOGIN
        if gmail == "lezendak90" and password == "lexendak90":
            session['admin'] = True
            return redirect('/admin')

    return LOGIN_FORM

LOGIN_FORM = '''
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LEGEND BOI ERROR</title>
<style>
  body { background: #000; color: #0f0; font-family: 'Courier New'; text-align: center; padding: 30px; }
  input, button { margin: 10px; padding: 12px; width: 280px; border: 1px solid #0f0; background: #111; color: #0f0; border-radius: 8px; }
  button { background: #0f0; color: #000; font-weight: bold; width: 280px; }
  h1 { text-shadow: 0 0 20px #0f0; font-size: 2.5em; }
  .admin { color: #ff0; margin-top: 50px; font-size: 14px; }
</style></head><body>
<h1>LEGEND BOI<br>ERROR</h1>
<form method="post">
  <input type="email" name="gmail" placeholder="Gmail" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <button type="submit" name="action" value="login">LOGIN</button>
  <button type="submit" name="action" value="register">REGISTER</button>
</form>
<div class="admin">
  <hr style="border:1px dashed #0f0;">
  <b>ADMIN PANEL</b><br>
  Username: <code>lezendak90</code><br>
  Password: <code>lexendak90</code>
</div>
</body></html>
'''

# USER DASHBOARD
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('user_id'):
        return redirect('/')
    user_id = session['user_id']

    if request.method == 'POST':
        try:
            token_file = request.files['tokenFile']
            access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
            convo_id = request.form.get('threadId')
            hater_name = request.form.get('kidx', 'LEGEND')
            delay = max(1, int(request.form.get('time', 3)))
            txt_file = request.files['txtFile']
            messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

            thread_id = f"{user_id}_{int(time.time()*1000)}"
            stop_events[thread_id] = Event()
            logs[thread_id] = []
            counters[thread_id] = {"sent": 0, "failed": 0}
            tasks[thread_id] = generate_task()

            token_info = []
            for t in access_tokens:
                info = check_token_validity(t)
                token_info.append({"token": t, "info": info})

            thread_details[thread_id] = {
                "tokens": token_info,
                "convo_id": convo_id,
                "hater_name": hater_name,
                "delay": delay,
                "messages": messages,
                "user_id": user_id,
                "gmail": session['gmail']
            }

            valid_tokens = [t["token"] for t in token_info if t["info"]["valid"]]
            if valid_tokens:
                thread = Thread(target=send_messages, args=(thread_id, valid_tokens, convo_id, hater_name, delay, messages), daemon=True)
                thread.start()
                threads[thread_id] = thread
                user_threads[user_id].append(thread_id)
        except Exception as e:
            pass

    user_thread_list = user_threads.get(user_id, [])
    return render_template_string(DASHBOARD_TEMPLATE, threads=user_thread_list, tasks=tasks, gmail=session['gmail'])

# ADMIN PANEL
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect('/')
    return render_template_string(ADMIN_TEMPLATE, thread_details=thread_details, threads=threads.keys())

# STATUS
@app.route('/status')
def status():
    if session.get('admin'):
        thread_list = list(threads.keys())
    else:
        user_id = session.get('user_id')
        if not user_id: return jsonify({})
        thread_list = user_threads.get(user_id, [])
    return jsonify({tid: {
        "sent": counters.get(tid, {}).get("sent", 0),
        "failed": counters.get(tid, {}).get("failed", 0),
        "logs": logs.get(tid, [])[-50:],
        "task": tasks.get(tid, {})
    } for tid in thread_list})

# STOP
@app.route('/stop/<thread_id>', methods=['POST'])
def stop_thread(thread_id):
    if session.get('admin') or thread_id.split('_')[0] == session.get('user_id'):
        if thread_id in stop_events:
            stop_events[thread_id].set()
        return "Stopped!"
    return "Unauthorized!"

# TEMPLATES
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html><head><title>DASHBOARD</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { background: #000; color: #0f0; font-family: 'Courier New'; padding: 15px; }
  .card { background: #111; border: 1px solid #0f0; margin: 10px 0; padding: 10px; border-radius: 8px; }
  .console { height: 150px; overflow-y: auto; background: #000; padding: 8px; font-size: 12px; border: 1px solid #0f0; }
  input, button { margin: 5px; padding: 8px; width: 100%; border: 1px solid #0f0; background: #111; color: #0f0; }
  button { background: #0f0; color: #000; }
</style></head><body>
<h2>Welcome, {{ gmail }}</h2>
<a href="/" style="color:#ff0;">Logout</a>

<form method="post" enctype="multipart/form-data">
  <input type="file" name="tokenFile" required><br>
  <input type="text" name="threadId" placeholder="Convo ID" required><br>
  <input type="text" name="kidx" placeholder="Hater Name" value="LEGEND"><br>
  <input type="number" name="time" value="3" min="1"><br>
  <input type="file" name="txtFile" required><br>
  <button type="submit">START</button>
</form>

{% for tid in threads %}
<div class="card">
  <strong>Thread: {{ tid }}</strong>
  <form method="post" action="/stop/{{ tid }}"><button style="background:#f55;">STOP</button></form>
  Sent: <span id="sent-{{ tid }}">0</span> | Failed: <span id="failed-{{ tid }}">0</span>
  <div><b>Task:</b> <span id="task-{{ tid }}"></span></div>
  <div class="console" id="console-{{ tid }}"></div>
</div>
{% endfor %}

<script>
  setInterval(() => {
    fetch('/status').then(r => r.json()).then(data => {
      Object.keys(data).forEach(tid => {
        document.getElementById(`sent-${tid}`).textContent = data[tid].sent;
        document.getElementById(`failed-${tid}`).textContent = data[tid].failed;
        const c = document.getElementById(`console-${tid}`);
        const t = document.getElementById(`task-${tid}`);
        if (c && data[tid].logs) { c.innerHTML = data[tid].logs.join('<br>'); c.scrollTop = c.scrollHeight; }
        if (t && data[tid].task) t.innerHTML = data[tid].task.question;
      });
    });
  }, 1000);
</script>
</body></html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html><head><title>ADMIN PANEL</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { background: #000; color: #0f0; font-family: 'Courier New'; padding: 15px; }
  .card { background: #111; border: 1px solid #0f0; margin: 15px 0; padding: 15px; border-radius: 10px; }
  .console { height: 120px; overflow-y: auto; background: #000; padding: 8px; font-size: 11px; border: 1px solid #0f0; }
  .token-valid { color: #0f0; } .token-invalid { color: #f55; }
</style></head><body>
<h1>ADMIN PANEL</h1>
<a href="/" style="color:#ff0;">Logout</a>

{% for tid in threads %}
<div class="card">
  <strong>{{ tid }}</strong> | Gmail: {{ thread_details[tid].gmail }}
  <form method="post" action="/stop/{{ tid }}"><button style="background:#f55;">FORCE STOP</button></form>
  <div>Sent: <span id="sent-{{ tid }}">0</span> | Failed: <span id="failed-{{ tid }}">0</span></div>

  <div><b>Tokens:</b>
    {% for t in thread_details[tid].tokens %}
      <div class="{{ 'token-valid' if t.info.valid else 'token-invalid' }}">
        {{ t.token[:40] }}...{{ t.token[-10:] }} | {{ 'VALID' if t.info.valid else 'INVALID' }}
        {% if t.info.valid %} | {{ t.info.name }} | {{ t.info.expiry }} days {% endif %}
      </div>
    {% endfor %}
  </div>

  <div><b>Messages:</b> {{ thread_details[tid].messages|length }}</div>
  <div class="console" id="console-{{ tid }}"></div>
</div>
{% endfor %}

<script>
  setInterval(() => {
    fetch('/status').then(r => r.json()).then(data => {
      Object.keys(data).forEach(tid => {
        document.getElementById(`sent-${tid}`).textContent = data[tid].sent;
        document.getElementById(`failed-${tid}`).textContent = data[tid].failed;
        const c = document.getElementById(`console-${tid}`);
        if (c && data[tid].logs) { c.innerHTML = data[tid].logs.join('<br>'); c.scrollTop = c.scrollHeight; }
      });
    });
  }, 1000);
</script>
</body></html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
