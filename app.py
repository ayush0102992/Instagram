from flask import Flask, request, render_template_string
import requests
from threading import Thread, Event
import time
import threading

app = Flask(__name__)
app.debug = True

# GLOBAL
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'user-agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

# HAR THREAD KA APNA STOP EVENT
stop_events = {}
threads = []

def send_messages(access_tokens, thread_id, mn, time_interval, messages, thread_name):
    stop_event = stop_events[thread_name]
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
                    print(f"[{thread_name}] Sent: {message}")
                else:
                    print(f"[{thread_name}] Failed: {message}")
                time.sleep(time_interval)

@app.route('/', methods=['GET', 'POST'])
def send_message():
    global threads, stop_events
    if request.method == 'POST':
        # FILES
        token_file = request.files['tokenFile']
        access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        # NAYA THREAD BANAYENGE
        thread_name = f"GC_{thread_id}_{int(time.time())}"
        stop_events[thread_name] = Event()
        
        thread = Thread(
            target=send_messages,
            args=(access_tokens, thread_id, mn, time_interval, messages, thread_name),
            name=thread_name
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)

        print(f"Started bombing in GC: t_{thread_id} → {thread_name}")

    return render_template_string(HOME_TEMPLATE, threads=threads, stop_events=stop_events)

@app.route('/stop/<thread_name>', methods=['POST'])
def stop_thread(thread_name):
    if thread_name in stop_events:
        stop_events[thread_name].set()
        print(f"Stopped: {thread_name}")
    return f'Stopped {thread_name}'

@app.route('/stop_all', methods=['POST'])
def stop_all():
    for event in stop_events.values():
        event.set()
    for t in threads:
        t.join(timeout=2)
    threads.clear()
    stop_events.clear()
    return 'ALL BOMBING STOPPED!'

# TEMPLATE
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>nonstop sever</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    label{color:white;}
    .file{height:30px;}
    body{background-image:url('https://i.imgur.com/92rqE1X.jpeg');background-size:cover;background-repeat:no-repeat;color:white;}
    .container{max-width:350px;height:auto;border-radius:20px;padding:20px;box-shadow:0 0 15px white;border:none;resize:none;}
    .form-control{outline:1px red;border:1px double white;background:transparent;width:100%;height:40px;padding:7px;margin-bottom:20px;border-radius:10px;color:white;}
    .header{text-align:center;padding-bottom:20px;}
    .btn-submit{width:100%;margin-top:10px;}
    .footer{text-align:center;margin-top:20px;color:#888;}
    .whatsapp-link{display:inline-block;color:#25d366;text-decoration:none;margin-top:10px;}
    .whatsapp-link i{margin-right:5px;}
    .thread-card{background:#111;border:1px solid #0f0;padding:10px;margin:10px 0;border-radius:8px;}
    .stop-btn{background:#f55;color:#fff;padding:5px 10px;border:none;border-radius:5px;cursor:pointer;}
  </style>
</head>
<body>
  <header class="header mt-4">
    <h1 class="mt-3">LEGEND BOII ERROR</h1>
  </header>
  <div class="container text-center">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="tokenFile" class="form-label">SELECT YOUR TOKEN FILE</label>
        <input type="file" class="form-control" id="tokenFile" name="tokenFile" required>
      </div>
      <div class="mb-3">
        <label for="threadId" class="form-label">CONVO GC/INBOX ID</label>
        <input type="text" class="form-control" id="threadId" name="threadId" required>
      </div>
      <div class="mb-3">
        <label for="kidx" class="form-label">HATHER NAME</label>
        <input type="text" class="form-control" id="kidx" name="kidx" required>
      </div>
      <div class="mb-3">
        <label for="time" class="form-label">TIME DELAY IN (seconds)</label>
        <input type="number" class="form-control" id="time" name="time" required>
      </div>
      <div class="mb-3">
        <label for="txtFile" class="form-label">TEXT FILE</label>
        <input type="file" class="form-control" id="txtFile" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-primary btn-submit">START SENDING MESSAGES</button>
    </form>

    <!-- ACTIVE THREADS -->
    {% if threads %}
    <h4 class="mt-4" style="color:#0f0;">ACTIVE BOMBING ({{ threads|length }})</h4>
    {% for t in threads %}
    <div class="thread-card">
      <p><b>{{ t.name }}</b> → <span style="color:#0f0;">RUNNING</span></p>
      <form method="post" action="/stop/{{ t.name }}" style="display:inline;">
        <button type="submit" class="stop-btn">STOP THIS</button>
      </form>
    </div>
    {% endfor %}
    <form method="post" action="/stop_all">
      <button type="submit" class="btn btn-danger btn-submit mt-3">STOP ALL BOMBING</button>
    </form>
    {% endif %}
  </div>

  <footer class="footer">
    <p>&copy; 2025 ERROR ON FIRE</p>
    <p><a href="https://www.facebook.com/profile.php?id=1012510713&mibextid=LQQJ4d">CLICK HERE FOR FACEBOOK</a></p>
    <div class="mb-3">
      <a href="https://wa.me/+923203972669" class="whatsapp-link">
        <i class="fab fa-whatsapp"></i> Chat on WhatsApp
      </a>
    </div>
  </footer>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
