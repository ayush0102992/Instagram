from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import secrets

app = Flask(__name__)
app.debug = True

# GLOBAL
headers = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'www.google.com'
}

# TASK MANAGEMENT
tasks = {}  # task_id -> {thread, stop_event, info}
active_threads = []

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = tasks[task_id]['stop_event']
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                if stop_event.is_set():
                    break
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = f"{mn} {message1}"
                parameters = {'access_token': access_token, 'message': message}
                response = requests.post(api_url, data=parameters, headers=headers)
                if response.status_code == 200:
                    print(f"[{task_id}] Sent: {message}")
                else:
                    print(f"[{task_id}] Failed: {message}")
                time.sleep(time_interval)

@app.route('/', methods=['GET', 'POST'])
def home():
    global tasks, active_threads
    message = ""

    if request.method == 'POST':
        action = request.form.get('action')

        # START BOMBING
        if action == 'start':
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

            thread_id = request.form.get('threadId')
            mn = request.form.get('kidx')
            time_interval = int(request.form.get('time'))

            txt_file = request.files['txtFile']
            messages = txt_file.read().decode().splitlines()

            # GENERATE TASK ID
            task_id = secrets.token_hex(4).upper()  # 8 char random
            stop_event = Event()

            thread = Thread(
                target=send_messages,
                args=(access_tokens, thread_id, mn, time_interval, messages, task_id)
            )
            thread.daemon = True
            thread.start()

            # SAVE TASK
            tasks[task_id] = {
                'thread': thread,
                'stop_event': stop_event,
                'info': {
                    'gc_id': f"t_{thread_id}",
                    'tokens': len(access_tokens),
                    'messages': len(messages),
                    'delay': time_interval,
                    'started': time.strftime("%H:%M:%S")
                }
            }
            active_threads.append(thread)
            message = f"<p style='color:#0f0;'>BOMBING STARTED! TASK ID: <b>{task_id}</b></p>"

        # STOP BY TASK ID
        elif action == 'stop':
            task_id = request.form.get('task_id', '').strip().upper()
            if task_id in tasks:
                tasks[task_id]['stop_event'].set()
                tasks[task_id]['thread'].join(timeout=2)
                del tasks[task_id]
                message = f"<p style='color:#f55;'>TASK {task_id} STOPPED!</p>"
            else:
                message = f"<p style='color:#f55;'>Invalid Task ID: {task_id}</p>"

        # STOP ALL
        elif action == 'stop_all':
            for task_id in list(tasks.keys()):
                tasks[task_id]['stop_event'].set()
                tasks[task_id]['thread'].join(timeout=2)
            tasks.clear()
            active_threads.clear()
            message = "<p style='color:#f55;'>ALL BOMBING STOPPED!</p>"

    return render_template_string(HOME_TEMPLATE, tasks=tasks, message=message)

# TEMPLATE
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FB BOMBER - TASK ID CONTROL</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    label{color:white;}
    body{background-image:url('https://i.imgur.com/92rqE1X.jpeg');background-size:cover;background-repeat:no-repeat;color:white;}
    .container{max-width:380px;margin:20px auto;padding:20px;border-radius:20px;box-shadow:0 0 20px white;}
    .form-control{background:transparent;border:1px solid white;color:white;border-radius:10px;}
    .btn-submit{width:100%;margin:10px 0;}
    .task-card{background:#111;border:1px solid #0f0;padding:12px;margin:10px 0;border-radius:10px;}
    .task-id{font-family:monospace;font-weight:bold;color:#0f0;}
    .stop-btn{background:#f55;color:white;border:none;padding:6px 12px;border-radius:5px;}
    .message{margin:15px 0;padding:10px;border-radius:8px;}
  </style>
</head>
<body>
  <div class="container text-center">
    <h1 class="mt-3" style="text-shadow:0 0 15px #0f0;">LEGEND BOMBER</h1>

    <!-- START FORM -->
    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="action" value="start">
      <div class="mb-3">
        <label>TOKEN FILE</label>
        <input type="file" class="form-control" name="tokenFile" required>
      </div>
      <div class="mb-3">
        <label>CONVO/GC ID</label>
        <input type="text" class="form-control" name="threadId" placeholder="123456789" required>
      </div>
      <div class="mb-3">
        <label>HATHER NAME</label>
        <input type="text" class="form-control" name="kidx" placeholder="LEGEND" required>
      </div>
      <div class="mb-3">
        <label>DELAY (sec)</label>
        <input type="number" class="form-control" name="time" value="5" required>
      </div>
      <div class="mb-3">
        <label>MESSAGE FILE</label>
        <input type="file" class="form-control" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-success btn-submit">START BOMBING</button>
    </form>

    <!-- STOP BY TASK ID -->
    <form method="post" class="mt-4">
      <input type="hidden" name="action" value="stop">
      <div class="input-group">
        <input type="text" class="form-control" name="task_id" placeholder="Enter Task ID to STOP" required>
        <button type="submit" class="btn btn-danger">STOP TASK</button>
      </div>
    </form>

    <!-- STOP ALL -->
    <form method="post">
      <input type="hidden" name="action" value="stop_all">
      <button type="submit" class="btn btn-danger btn-submit mt-3">STOP ALL BOMBING</button>
    </form>

    <!-- MESSAGE -->
    {{ message|safe }}

    <!-- ACTIVE TASKS -->
    {% if tasks %}
    <h4 class="mt-4" style="color:#0f0;">ACTIVE TASKS ({{ tasks|length }})</h4>
    {% for task_id, data in tasks.items() %}
    <div class="task-card">
      <p><span class="task-id">{{ task_id }}</span></p>
      <p>GC: <b>{{ data.info.gc_id }}</b></p>
      <p>Tokens: {{ data.info.tokens }} | Msgs: {{ data.info.messages }} | Delay: {{ data.info.delay }}s</p>
      <p>Started: {{ data.info.started }}</p>
      <form method="post" style="display:inline;">
        <input type="hidden" name="action" value="stop">
        <input type="hidden" name="task_id" value="{{ task_id }}">
        <button type="submit" class="stop-btn">STOP THIS</button>
      </form>
    </div>
    {% endfor %}
    {% else %}
    <p class="mt-4" style="color:#888;">No active bombing.</p>
    {% endif %}
  </div>

  <footer class="text-center mt-4" style="color:#888;">
    <p>© 2025 LEGEND BOII ERROR</p>
    <p><a href="https://facebook.com" style="color:#25d366;">FB</a> | 
       <a href="https://wa.me/+923203972669" style="color:#25d366;">WhatsApp</a></p>
  </footer>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
