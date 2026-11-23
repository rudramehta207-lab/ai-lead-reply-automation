import csv
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template_string, request
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY", "")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
CSV_FILE = os.path.join(BASE_DIR, "leads.csv")


def generate_reply(customer_name, customer_message):
    if not API_KEY:
        return "Error: GEMINI_API_KEY not found in .env file."

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a polite receptionist for Apex Coaching Center in Ahmedabad. "
                            "Timings: 9 AM to 7 PM (Mon-Sat). Monthly fee: Rs 2,500. "
                            f"Greet {customer_name} by name and reply in 2 short, helpful lines "
                            f"to this inquiry: {customer_message}"
                        )
                    }
                ]
            }
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(URL, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif response.status_code == 503:
                time.sleep(2)
            else:
                return f"API Error {response.status_code}"
        except requests.exceptions.RequestException:
            return "Connection failed. Please try again."

    return "Server is busy right now. Please try again in a moment."


def save_lead(name, phone, message, reply):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Name", "Phone", "Question", "AI Reply"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            phone,
            message,
            reply,
        ])


def get_recent_leads():
    if not os.path.isfile(CSV_FILE):
        return []
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-5:][::-1]


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Instant Lead-Reply Demo</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; max-width: 720px; margin: 35px auto; padding: 0 16px; }
        .card { background: white; padding: 24px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px; }
        h2 { margin-top: 0; color: #1e293b; }
        input, textarea { width: 100%; padding: 10px; margin: 8px 0 14px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; }
        button { background: #2563eb; color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-size: 15px; width: 100%; }
        button:hover { background: #1d4ed8; }
        .reply-box { background: #ecfdf5; border-left: 4px solid #10b981; padding: 14px; margin-top: 16px; border-radius: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Apex Coaching Center - Quick Inquiry</h2>
        <form method="POST">
            <input type="text" name="name" placeholder="Your Name" required>
            <input type="text" name="phone" placeholder="WhatsApp / Phone Number" required>
            <textarea name="message" rows="3" placeholder="Ask about fees, timings, or batches..." required></textarea>
            <button type="submit">Send Inquiry</button>
        </form>

        {% if ai_reply %}
        <div class="reply-box">
            <strong>Instant AI Reply:</strong><br>{{ ai_reply }}
        </div>
        {% endif %}
    </div>

    <div class="card">
        <h3>Saved Leads (Auto-synced to leads.csv)</h3>
        {% if leads %}
        <table>
            <tr><th>Time</th><th>Name</th><th>Phone</th><th>Question</th></tr>
            {% for lead in leads %}
            <tr>
                <td>{{ lead['Timestamp'] }}</td>
                <td>{{ lead['Name'] }}</td>
                <td>{{ lead['Phone'] }}</td>
                <td>{{ lead['Question'] }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>No leads yet. Submit the form above to test.</p>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    ai_reply = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        if name and phone and message:
            ai_reply = generate_reply(name, message)
            save_lead(name, phone, message, ai_reply)
    return render_template_string(HTML_PAGE, ai_reply=ai_reply, leads=get_recent_leads())


if __name__ == "__main__":
    app.run(debug=True)
