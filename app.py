from flask import Flask, request, render_template_string, jsonify, session, redirect
import requests
from threading import Thread, Event
import time
import random
import string
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Global Storage
threads = {}
stop_events = {}
tasks = {}
counters = {}
logs = {}
user_threads = {}
thread_details = {}  # NEW: thread_id -> {token, convo_id, hater_name, delay, messages, user_id}

headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

def generate_task():
    types = ["math", "captcha", "reverse"]
    t = random.choice(types)
    if t == "math":
        a, b = random.randint(1, 15), random.randint(1, 15)
        return {"type": "math", "question": f"{a} + {b} = ?", "answer": str(a + b)}
    elif t == "captcha":
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        return {"type": "captcha", "question": f"Type: <code>{code}</code>", "answer": code}
    elif t == "reverse":
        word = random.choice(["LEGEND", "ERROR", "BOI", "FIRE", "STOP"])
        return {"type": "reverse", "question": f"Reverse: <b>{word}</b>", "answer": word[::-1]}

def send_messages(thread_id, access_tokens, convo_id, hater_name, delay, messages):
    stop_event = stop_events[thread_id]
    sent = failed = 0
    logs[thread_id] = []

    while not stop_event.is_set():
        for msg_text in messages:
            if stop_event.is_set(): break
            for token in access_tokens:
                if stop_event.is_set(): break
                url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
                full_msg = f"{hater_name} {msg_text.strip()}"
                params = {'access_token': token, 'message': full_msg}

                try:
                    r = requests.post(url, data=params, headers=headers, timeout=10)
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

    for d in [threads, stop_events, tasks, counters, logs, thread_details]:
        d.pop(thread_id, None)

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == "admin" and password == "error2025":
            session['admin'] = True
            return redirect('/admin')
        elif username == "" and password == "legend123":
            session['user_id'] = secrets.token_hex(8)
            if session['user_id'] not in user_threads:
                user_threads[session['user_id']] = []
            return redirect('/')
        else:
            return '''
            <div style="color:#f55; text-align:center; margin:20px;">
              WRONG CREDENTIALS!
            </div>
            ''' + LOGIN_FORM

    return LOGIN_FORM

LOGIN_FORM = '''
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOGIN</title>
<style>
  body { background: #000; color: #0f0; font-family: 'Courier New'; text-align: center; padding: 50px; }
  input, button { margin: 10px; padding: 12px; width: 280px; border: 1px solid #0f0; background: #111; color: #0f0; border-radius: 8px; }
  button { background: #0f0; color: #000; font-weight: bold; }
  h1 { text-shadow: 0 0 15px #0f0; }
</style>
</head>
<body>
  <h1>LEGEND BOI ERROR</h1>
  <form method="post">
    <input type="text" name="username" placeholder="Username (admin for panel)" autocomplete="off"><br>
    <input type="password" name="password" placeholder="Password" required><br>
    <button type="submit">LOGIN</button>
  </form>
  <p style="color:#ff0;font-size:12px;">User: leave username blank | Admin: admin / error2025</p>
</body>
</html>
'''

# USER DASHBOARD
@app.route('/', methods=['GET', 'POST'])
def user_dashboard():
    if not session.get('user_id') and not session.get('admin'):
        return redirect('/login')

    user_id = session.get('user_id')
    if user_id and user_id not in user_threads:
        user_threads[user_id] = []

    if request.method == 'POST' and user_id:
        try:
            token_file = request.files['tokenFile']
            access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
            convo_id = request.form.get('threadId', '').strip()
            hater_name = request.form.get('kidx', 'LEGEND').strip()
            delay = max(1, int(request.form.get('time', 3)))
            txt_file = request.files['txtFile']
            messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

            if not access_tokens or not messages or not convo_id:
                return "Invalid!", 400

            thread_id = f"{user_id}_{int(time.time()*1000)}"
            stop_events[thread_id] = Event()
            logs[thread_id] = []
            counters[thread_id] = {"sent": 0, "failed": 0}
            tasks[thread_id] = generate_task()

            # SAVE FULL DETAILS FOR ADMIN
            thread_details[thread_id] = {
                "tokens": access_tokens,
                "convo_id": convo_id,
                "hater_name": hater_name,
                "delay": delay,
                "messages": messages,
                "user_id": user_id
            }

            thread = Thread(target=send_messages, args=(thread_id, access_tokens, convo_id, hater_name, delay, messages), daemon=True)
            thread.start()
            threads[thread_id] = thread
            user_threads[user_id].append(thread_id)
        except Exception as e:
            return f"Error: {str(e)}", 500

    user_thread_list = user_threads.get(user_id, []) if user_id else []
    return render_template_string(USER_TEMPLATE, threads=user_thread_list, tasks=tasks)

# ADMIN PANEL WITH FULL DETAILS
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        return redirect('/login')

    total_users = len(user_threads)
    total_threads = len(threads)

    return render_template_string(ADMIN_TEMPLATE,
           threads=threads.keys(), tasks=tasks, counters=counters, logs=logs,
           thread_details=thread_details, total_users=total_users, total_threads=total_threads)

# STOP THREAD
@app.route('/stop/<thread_id>', methods=['POST'])
def stop_thread(thread_id):
    if session.get('admin'):
        if thread_id in stop_events:
            stop_events[thread_id].set()
        return "FORCE STOPPED!"

    user_answer = request.form.get('answer', '').strip()
    correct = tasks.get(thread_id, {}).get("answer", "").strip()
    if user_answer.lower() == correct.lower():
        if thread_id in stop_events:
            stop_events[thread_id].set()
        return "TASK SOLVED!"
    return "WRONG!"

@app.route('/stop_all', methods=['POST'])
def stop_all():
    for event in stop_events.values():
        event.set()
    return "ALL STOPPED!"

@app.route('/status')
def status():
    if session.get('admin'):
        thread_list = list(threads.keys())
    else:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({})
        thread_list = user_threads.get(user_id, [])

    return jsonify({
        tid: {
            "sent": counters.get(tid, {}).get("sent", 0),
            "failed": counters.get(tid, {}).get("failed", 0),
            "logs": logs.get(tid, [])[-50:],
            "task": tasks.get(tid, {})
        } for tid in thread_list
    })

# TEMPLATES
USER_TEMPLATE = '''... [same as before] ...'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <title>ADMIN PANEL - FULL CONTROL</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background: #000; color: #0f0; font-family: 'Courier New'; padding: 15px; }
    .stats { background: #111; padding: 15px; border: 1px solid #0f0; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .card { background: #111; border: 1px solid #0f0; margin: 15px 0; padding: 15px; border-radius: 10px; }
    .console { background: #000; color: #0f0; height: 150px; overflow-y: auto; padding: 8px; font-size: 11px; border: 1px solid #0f0; border-radius: 5px; }
    .detail { background: #222; padding: 10px; margin: 5px 0; border-radius: 5px; font-size: 12px; word-break: break-all; }
    h1, h2 { text-shadow: 0 0 10px #0f0; }
    .btn-stop { background: #f55; color: #fff; border: none; padding: 6px 12px; border-radius: 5px; }
    .logout { float: right; color: #ff0; text-decoration: none; }
    .token { color: #0ff; }
    .msg { color: #ff0; }
  </style>
</head>
<body>
  <h1 class="text-center">ADMIN PANEL - FULL DETAILS</h1>
  <a href="/login" class="logout">Logout</a>
  <div class="stats">
    <h3>Users: {{ total_users }} | Threads: {{ total_threads }}</h3>
  </div>

  {% for tid in threads %}
  <div class="card">
    <div class="d-flex justify-content-between">
      <strong>Thread: {{ tid }}</strong>
      <form method="post" action="/stop/{{ tid }}" style="display:inline;">
        <input type="hidden" name="answer" value="force">
        <button type="submit" class="btn-stop">FORCE STOP</button>
      </form>
    </div>

    <div><b>Sent:</b> <span id="sent-{{ tid }}">0</span> | <b>Failed:</b> <span id="failed-{{ tid }}">0</span></div>

    {% set details = thread_details.get(tid, {}) %}
    <div class="detail"><b>User ID:</b> {{ details.user_id }}</div>
    <div class="detail"><b>Convo ID:</b> {{ details.convo_id }}</div>
    <div class="detail"><b>Hater Name:</b> {{ details.hater_name }}</div>
    <div class="detail"><b>Delay:</b> {{ details.delay }}s</div>

    <div class="detail"><b>Tokens ({{ details.tokens|length }}):</b><br>
      {% for token in details.tokens %}
        <span class="token">{{ token[:40] }}...{{ token[-10:] }}</span><br>
      {% endfor %}
    </div>

    <div class="detail"><b>Messages ({{ details.messages|length }}):</b><br>
      {% for msg in details.messages[:5] %}
        <span class="msg">{{ details.hater_name }} {{ msg }}</span><br>
      {% endfor %}
      {% if details.messages|length > 5 %}<i>...{{ details.messages|length - 5 }} more</i>{% endif %}
    </div>

    <div><b>Task:</b> <span id="task-{{ tid }}">Loading...</span></div>
    <div class="console" id="console-{{ tid }}">Loading...</div>
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
</body>
</html>
'''

if __name__ == '__main__':
    print("LEGEND BOI ERROR SERVER STARTED!")
    print("User Password: legend123")
    print("Admin: username=admin, pass=error2025")
    app.run(host='0.0.0.0', port=5000, threaded=True)
