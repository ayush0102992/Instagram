from flask import Flask, request, render_template_string
from instagrapi import Client
import threading
import time
import os
import json

app = Flask(__name__)

# Render-compatible upload directory
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Global variables (basic state tracking)
messages = []
interval = 0
thread_id = ""
prefix = ""
cl = None
running = False
lock = threading.Lock()  # To prevent race conditions


# Function to send messages continuously
def send_messages():
    global messages, interval, thread_id, prefix, cl, running
    for message in messages:
        with lock:
            if not running:
                break
        try:
            full_message = f"{prefix} {message}" if prefix else message
            cl.direct_send(full_message, [thread_id])
            print(f"Message sent: {full_message}")
        except Exception as e:
            print(f"Error while sending message: {e}")
        time.sleep(interval)


# HTML UI Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Group Message Sender</title>
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #1e3c72, #2a5298, #4facfe);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
            position: relative;
        }
        body::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
            animation: pulse 10s infinite ease-in-out;
            z-index: -1;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .container {
            max-width: 650px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            border: 2px solid rgba(255, 255, 255, 0.2);
            animation: neonGlow 2s ease-in-out infinite alternate;
            position: relative;
            overflow: hidden;
        }
        @keyframes neonGlow {
            from {
                box-shadow: 0 0 15px #4facfe, 0 0 30px #2a5298;
            }
            to {
                box-shadow: 0 0 25px #00eaff, 0 0 50px #a3e4ff;
            }
        }
        .container::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(45deg, #00eaff, #a3e4ff, #4facfe);
            z-index: -1;
            filter: blur(10px);
            animation: borderGlow 3s infinite;
        }
        @keyframes borderGlow {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        h1 {
            font-size: 2.8em;
            text-align: center;
            color: #00eaff;
            text-shadow: 0 0 15px #00eaff, 0 0 30px #a3e4ff;
            margin-bottom: 25px;
            font-weight: 600;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        input[type="text"], input[type="number"], textarea, input[type="file"] {
            padding: 15px;
            font-size: 1.1em;
            border: none;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            outline: none;
            transition: all 0.4s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: inset 0 0 10px rgba(0, 234, 255, 0.1);
        }
        textarea {
            resize: vertical;
            min-height: 120px;
            line-height: 1.5;
        }
        input[type="file"]::file-selector-button {
            background: linear-gradient(45deg, #00eaff, #4facfe);
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.4s ease;
        }
        input[type="file"]::file-selector-button:hover {
            background: linear-gradient(45deg, #00b4cc, #2a5298);
            box-shadow: 0 5px 15px rgba(0, 234, 255, 0.4);
        }
        input:focus, textarea:focus {
            background: rgba(255, 255, 255, 0.2);
            box-shadow: 0 0 20px #00eaff, 0 0 40px #a3e4ff;
            transform: scale(1.02);
        }
        input::placeholder, textarea::placeholder {
            color: rgba(255, 255, 255, 0.5);
            font-style: italic;
        }
        button {
            padding: 15px 30px;
            font-size: 1.2em;
            background: linear-gradient(45deg, #00eaff, #4facfe);
            color: #fff;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.4s ease;
            box-shadow: 0 5px 20px rgba(0, 234, 255, 0.4);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        button:hover {
            background: linear-gradient(45deg, #00b4cc, #2a5298);
            box-shadow: 0 8px 30px rgba(0, 234, 255, 0.6);
            transform: translateY(-3px) scale(1.05);
        }
        button.stop {
            background: linear-gradient(45deg, #ff4d4d, #ff8c8c);
        }
        button.stop:hover {
            background: linear-gradient(45deg, #cc0000, #ff6666);
            box-shadow: 0 8px 30px rgba(255, 77, 77, 0.6);
        }
        p {
            font-size: 1.2em;
            text-align: center;
            color: #a3e4ff;
            text-shadow: 0 0 10px #a3e4ff, 0 0 20px #00eaff;
            margin-top: 25px;
            font-weight: 500;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1>Instagram Group Message Sender</h1>
        <form method="POST" action="/" enctype="multipart/form-data">
            <input type="file" name="cookies_file" accept=".txt" required placeholder="Upload cookies.txt">
            <textarea name="messages" placeholder="Enter messages (one per line)" required></textarea>
            <input type="text" name="thread_id" placeholder="Group Thread ID" required>
            <input type="number" name="interval" placeholder="Interval (seconds)" required>
            <input type="text" name="prefix" placeholder="Prefix (e.g., [Bot])">
            <button type="submit">Start Sending</button>
        </form>
        <form method="POST" action="/stop">
            <button type="submit" class="stop">Stop Sending</button>
        </form>
        <p>{{ status | safe }}</p>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    global messages, interval, thread_id, prefix, cl, running
    status = "Enter details to start sending messages."

    if request.method == "POST":
        try:
            thread_id = request.form["thread_id"].strip()
            interval = int(request.form["interval"])
            prefix = request.form.get("prefix", "").strip()

            # Handle cookies file upload
            cookies_file = request.files.get("cookies_file")
            if not cookies_file or cookies_file.filename == "":
                return render_template_string(HTML_TEMPLATE, status="Please upload cookies.txt")

            cookies_path = os.path.join(app.config["UPLOAD_FOLDER"], "cookies.txt")
            cookies_file.save(cookies_path)

            # Load cookies safely (JSON format)
            with open(cookies_path, "r") as f:
                cookies = json.load(f)

            # Initialize Instagram client
            cl = Client()
            cl.login_by_sessionid(cookies["sessionid"])

            # Load and clean messages
            messages = [m.strip() for m in request.form["messages"].split("\n") if m.strip()]

            # Start sending in background
            with lock:
                running = True
            threading.Thread(target=send_messages, daemon=True).start()

            status = "✅ Messages are being sent!"
        except Exception as e:
            status = f"❌ Error: {str(e)}"

    return render_template_string(HTML_TEMPLATE, status=status)


@app.route("/stop", methods=["POST"])
def stop():
    global running
    with lock:
        running = False
    return render_template_string(HTML_TEMPLATE, status="🛑 Stopped sending messages.")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
