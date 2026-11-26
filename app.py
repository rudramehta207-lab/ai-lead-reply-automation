import csv
import hmac
import os
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Flask,
    make_response,
    redirect,
    render_template_string,
    request,
    send_file,
    session,
    url_for,
)
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip().strip('"').strip("'")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
CSV_FILE = os.path.join(BASE_DIR, "leads.csv")
CSV_HEADERS = ["Timestamp", "Name", "Phone", "Question", "AI Reply"]

csv_lock = threading.Lock()


def normalize_name(name):
    return " ".join(name.strip().lower().split())


def normalize_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


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
                            "You are a polite receptionist for Apex Coaching Center in Ahmedabad.\n"
                            "Facts: Timings are 9 AM to 7 PM (Mon-Sat). Monthly fee is Rs 2,500.\n"
                            f"Customer Name: {customer_name}\n"
                            f"Customer Question: {customer_message}\n\n"
                            "Output Rules:\n"
                            "- Do NOT write in paragraph form.\n"
                            "- Reply ONLY in 3 to 4 short bullet points, each on a new line starting with '• '.\n"
                            "- First point must greet the customer by name.\n"
                            "- Do NOT use markdown bold (**), asterisks, or numbering.\n"
                            "- Keep each point short, clear, and accurate."
                        )
                    }
                ]
            }
        ]
    }

    for attempt in range(3):
        try:
            response = requests.post(URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text.replace("**", "")
            if response.status_code in (429, 503):
                print(f"[Attempt {attempt + 1}/3] Gemini {response.status_code}, retrying...")
                time.sleep(2 * (attempt + 1))
                continue
            print(f"API Error {response.status_code}: {response.text}")
            return f"API Error {response.status_code}. Check terminal for details."
        except requests.exceptions.InvalidHeader as e:
            print("HEADER ERROR (check GEMINI_API_KEY in .env):", repr(e))
            return "Configuration error: Invalid API key format in .env."
        except (KeyError, IndexError, ValueError) as e:
            print("RESPONSE PARSE ERROR:", repr(e))
            return "Received an unexpected AI response. Please try again."
        except requests.exceptions.RequestException as e:
            print(f"[Attempt {attempt + 1}/3] CONNECTION ERROR:", repr(e))
            if attempt < 2:
                time.sleep(2)
            else:
                return "Connection failed. Check VS Code terminal for exact error."

    return "Server is busy right now. Please try again in a moment."


def read_leads():
    if not os.path.isfile(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        return []

    with csv_lock:
        with open(CSV_FILE, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "Name" not in reader.fieldnames:
                return []
            return [
                row
                for row in reader
                if any((value or "").strip() for value in row.values())
            ]


def save_lead(name, phone, message, reply):
    with csv_lock:
        needs_header = (not os.path.isfile(CSV_FILE)) or (os.path.getsize(CSV_FILE) == 0)
        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if needs_header:
                writer.writerow(CSV_HEADERS)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                phone,
                message,
                reply,
            ])


def get_all_leads():
    return read_leads()[::-1]


def get_user_history(name, phone):
    target_name = normalize_name(name)
    target_phone = normalize_phone(phone)
    if not target_name or not target_phone:
        return []

    matches = [
        row
        for row in read_leads()
        if normalize_name(row.get("Name", "")) == target_name
        and normalize_phone(row.get("Phone", "")) == target_phone
    ]
    return matches[::-1]


PUBLIC_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apex Coaching Center - Quick Inquiry</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #0f172a; }
        .card { background: white; padding: 26px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 20px; }
        h2, h3 { margin-top: 0; color: #1e293b; }
        input, textarea { width: 100%; padding: 10px 12px; margin: 8px 0 14px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        input:focus, textarea:focus { outline: none; border-color: #2563eb; }
        button { background: #2563eb; color: white; border: none; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: bold; width: 100%; }
        button:hover { background: #1d4ed8; }
        button:disabled { background: #94a3b8; cursor: not-allowed; }
        .error-box { background: #fee2e2; color: #b91c1c; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 14px; }
        .reply-box { background: #ecfdf5; border-left: 4px solid #10b981; padding: 14px 16px; margin-top: 16px; border-radius: 6px; }
        .reply-text { white-space: pre-wrap; line-height: 1.65; margin-top: 6px; color: #0f172a; }
        .history-item { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; }
        .history-time { font-size: 12px; color: #64748b; margin-bottom: 6px; }
        .history-q { font-weight: bold; color: #1e293b; margin-bottom: 6px; }
        .privacy-note { font-size: 12px; color: #64748b; margin-top: 14px; text-align: center; }
        .footer { text-align: center; margin-top: 12px; font-size: 13px; }
        .footer a { color: #64748b; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Apex Coaching Center - Quick Inquiry</h2>
        {% if error %}<div class="error-box">{{ error }}</div>{% endif %}
        <form method="POST" id="inquiryForm">
            <input type="text" name="name" placeholder="Your Name" value="{{ form_name }}" required>
            <input type="tel" name="phone" placeholder="10-digit WhatsApp / Phone Number" value="{{ form_phone }}" required>
            <textarea name="message" rows="3" placeholder="Ask about fees, timings, or batches..." required>{{ form_message }}</textarea>
            <button type="submit" id="submitBtn">Send Inquiry</button>
        </form>

        {% if ai_reply %}
        <div class="reply-box">
            <strong>Instant AI Reply:</strong>
            <div class="reply-text">{{ ai_reply }}</div>
        </div>
        {% endif %}

        <p class="privacy-note">Your contact details are kept private and visible only to you and authorized staff.</p>
    </div>

    {% if previous_history %}
    <div class="card">
        <h3>Welcome back, {{ customer_name }} — Your Previous Inquiries</h3>
        {% for item in previous_history %}
        <div class="history-item">
            <div class="history-time">{{ item.get('Timestamp', '') }}</div>
            <div class="history-q">Question: {{ item.get('Question', '') }}</div>
            <div class="reply-text">{{ item.get('AI Reply', '') }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="footer">
        <a href="/admin">Staff Admin Login</a>
    </div>

    <script>
        document.getElementById("inquiryForm").addEventListener("submit", function () {
            const btn = document.getElementById("submitBtn");
            btn.disabled = true;
            btn.textContent = "Generating AI Reply...";
        });
    </script>
</body>
</html>
"""

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; max-width: 420px; margin: 70px auto; padding: 0 16px; }
        .card { background: white; padding: 26px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
        h2 { margin-top: 0; color: #1e293b; }
        input { width: 100%; padding: 10px 12px; margin: 10px 0 16px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; }
        button { background: #1e293b; color: white; border: none; padding: 12px; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: bold; width: 100%; }
        button:hover { background: #0f172a; }
        .error { color: #b91c1c; background: #fee2e2; padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 14px; }
        .back { display: block; text-align: center; margin-top: 14px; font-size: 13px; color: #2563eb; text-decoration: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Staff Admin Login</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Admin Password" required autofocus>
            <button type="submit">Unlock Lead Dashboard</button>
        </form>
        <a class="back" href="/">Back to Inquiry Form</a>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - Saved Leads</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; max-width: 1000px; margin: 35px auto; padding: 0 16px; color: #0f172a; }
        .card { background: white; padding: 24px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
        .top-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }
        h2 { margin: 0; color: #1e293b; }
        .badge { background: #dbeafe; color: #1d4ed8; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: bold; margin-left: 8px; }
        .actions { display: flex; gap: 8px; }
        .btn { color: white; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: bold; }
        .btn-blue { background: #2563eb; }
        .btn-gray { background: #475569; }
        .btn-red { background: #dc2626; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
        th { background: #f8fafc; white-space: nowrap; }
        .reply-cell { white-space: pre-wrap; line-height: 1.5; min-width: 240px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="top-bar">
            <h2>
                Private Lead Dashboard
                <span class="badge">{{ leads|length }} Lead{{ '' if leads|length == 1 else 's' }}</span>
            </h2>
            <div class="actions">
                <a class="btn btn-gray" href="/">Inquiry Form</a>
                {% if leads %}
                <a class="btn btn-blue" href="/admin/download">Download CSV</a>
                {% endif %}
                <a class="btn btn-red" href="/logout">Logout</a>
            </div>
        </div>
        {% if leads %}
        <div class="table-wrap">
            <table>
                <tr><th>Time</th><th>Name</th><th>Phone</th><th>Question</th><th>AI Reply</th></tr>
                {% for lead in leads %}
                <tr>
                    <td style="white-space: nowrap;">{{ lead.get('Timestamp', '') }}</td>
                    <td>{{ lead.get('Name', '') }}</td>
                    <td style="white-space: nowrap;">{{ lead.get('Phone', '') }}</td>
                    <td>{{ lead.get('Question', '') }}</td>
                    <td class="reply-cell">{{ lead.get('AI Reply', '') }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% else %}
        <p>No leads saved yet.</p>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    ai_reply = None
    previous_history = []
    customer_name = ""
    error = None
    form_name = ""
    form_phone = ""
    form_message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not phone or not message:
            error = "Please fill in your name, phone number, and inquiry."
            form_name, form_phone, form_message = name, phone, message
        elif len(normalize_phone(phone)) < 10:
            error = "Please enter a valid 10-digit phone number."
            form_name, form_phone, form_message = name, phone, message
        else:
            customer_name = name
            previous_history = get_user_history(name, phone)
            ai_reply = generate_reply(name, message)
            save_lead(name, phone, message, ai_reply)

    return render_template_string(
        PUBLIC_HTML,
        ai_reply=ai_reply,
        previous_history=previous_history,
        customer_name=customer_name,
        error=error,
        form_name=form_name,
        form_phone=form_phone,
        form_message=form_message,
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not ADMIN_PASSWORD:
        return render_template_string(
            ADMIN_LOGIN_HTML,
            error="ADMIN_PASSWORD is not set in .env file.",
        )

    if session.get("is_admin"):
        response = make_response(
            render_template_string(ADMIN_DASHBOARD_HTML, leads=get_all_leads())
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    error = None
    if request.method == "POST":
        entered = request.form.get("password", "")
        if hmac.compare_digest(entered, ADMIN_PASSWORD):
            session["is_admin"] = True
            return redirect(url_for("admin"))
        error = "Incorrect password."

    return render_template_string(ADMIN_LOGIN_HTML, error=error)


@app.route("/admin/download")
def download_csv():
    if not session.get("is_admin"):
        return redirect(url_for("admin"))
    if not os.path.isfile(CSV_FILE):
        return redirect(url_for("admin"))
    return send_file(CSV_FILE, as_attachment=True, download_name="leads.csv")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
