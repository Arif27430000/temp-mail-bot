import os
import random
import string
import telebot
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Direct Bot Token
TOKEN = "8953590306:AAFfDTe3BxPnp0PhogapywtSzSeWPPmobjo"
bot = telebot.TeleBot(TOKEN)

# Databases
user_emails = {}   
email_inboxes = {} 

def generate_random_prefix(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- PREMIUM TEMP-MAIL.ORG WEB INTERFACE CLONE ---
WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Temp Mail - Disposable Temporary Email</title>
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; background-color: #1e2026; color: #ffffff; margin: 0; padding: 0; display: flex; flex-direction: column; align-items: center; }
        .navbar { width: 100%; max-width: 600px; padding: 20px; display: flex; justify-content: space-between; align-items: center; box-sizing: border-box; }
        .logo { font-size: 24px; font-weight: 800; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
        .logo span { color: #00cd84; }
        .premium-badge { background-color: #f7e115; color: #000000; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; text-decoration: none; }
        
        .main-card { background-color: #262932; width: 92%; max-width: 550px; border-radius: 12px; padding: 30px 20px; margin-top: 20px; box-sizing: border-box; border: 1px dashed #3d4352; text-align: center; position: relative; }
        .card-title { font-size: 20px; color: #a2a8b5; font-weight: 500; margin-bottom: 20px; }
        .email-display { width: 100%; background-color: #1a1c22; border: none; padding: 18px 12px; border-radius: 8px; color: #ffffff; font-size: 18px; font-weight: 600; text-align: center; box-sizing: border-box; margin-bottom: 20px; outline: none; }
        
        .action-row { display: flex; gap: 12px; justify-content: center; margin-bottom: 10px; }
        .btn-action { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 14px 28px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; border: none; text-decoration: none; min-width: 130px; }
        .btn-qr { background-color: #3b3f4d; color: #ffffff; }
        .btn-copy { background-color: #00cd84; color: #ffffff; width: 100%; }
        
        .control-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; width: 92%; max-width: 550px; margin-top: 20px; }
        .btn-ctrl { background-color: #ffffff; color: #262932; padding: 14px; border-radius: 8px; font-weight: 600; text-decoration: none; border: none; font-size: 15px; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; align-items: center; justify-content: center; gap: 8px; }
        
        .inbox-container { width: 92%; max-width: 550px; background-color: #262932; border-radius: 12px; margin-top: 25px; box-sizing: border-box; overflow: hidden; margin-bottom: 50px; }
        .inbox-header { background-color: #1a1c22; padding: 15px 20px; font-weight: bold; font-size: 16px; color: #a2a8b5; text-align: left; }
        .inbox-body { padding: 40px 20px; text-align: center; background-color: #262932; }
        .empty-icon { width: 64px; height: 64px; opacity: 0.3; margin-bottom: 15px; }
        .empty-text { font-size: 18px; color: #ffffff; font-weight: 500; margin-bottom: 5px; }
        .empty-subtext { font-size: 14px; color: #697080; }
        
        .mail-item { padding: 15px 20px; border-bottom: 1px solid #3d4352; text-align: left; }
        .mail-sender { font-weight: bold; color: #00cd84; font-size: 14px; margin-bottom: 30px; }
        .mail-subject { font-weight: 600; font-size: 16px; margin-bottom: 5px; }
        .mail-body { color: #a2a8b5; font-size: 14px; white-space: pre-wrap; }
    </style>
</head>
<body>

    <div class="navbar">
        <div class="logo">✉️ TEMP<span>MAIL</span></div>
        <a href="#" class="premium-badge">Premium</a>
    </div>

    <div class="main-card">
        <div class="card-title">Your Temporary Email Address</div>
        <input class="email-display" type="text" value="{{ prefix }}@fixscal.com" readonly id="mailBox">
        <div class="action-row">
            <button class="btn-action btn-qr">🔳 QR code</button>
            <button class="btn-action btn-copy" onclick="navigator.clipboard.writeText('{{ prefix }}@fixscal.com'); alert('Copied!');">📋 Copy</button>
        </div>
    </div>

    <div class="control-grid">
        <button class="btn-ctrl" onclick="navigator.clipboard.writeText('{{ prefix }}@fixscal.com');">📄 Copy</button>
        <a href="/" class="btn-ctrl">🔄 Refresh</a>
        <a href="/change" class="btn-ctrl">✏️ Change</a>
        <a href="/delete" class="btn-ctrl" style="color: #ff4a4a;">❌ Delete</a>
    </div>

    <div class="inbox-container">
        <div class="inbox-header">INBOX</div>
        <div class="inbox-body">
            {% if emails %}
                {% for mail in emails %}
                    <div class="mail-item">
                        <div class="mail-sender">From: {{ mail.sender }}</div>
                        <div class="mail-subject">Subject: {{ mail.subject }}</div>
                        <div class="mail-body">{{ mail.body }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <img class="empty-icon" src="https://cdn-icons-png.flaticon.com/512/6584/6584934.png" alt="Mail">
                <div class="empty-text">Your inbox is empty</div>
                <div class="empty-subtext">Waiting for incoming emails</div>
            {% endif %}
        </div>
    </div>

</body>
</html>
"""

@app.route('/')
def web_home():
    current_prefix = request.cookies.get('web_prefix')
    if not current_prefix:
        current_prefix = f"user_{generate_random_prefix()}"
    if current_prefix not in email_inboxes:
        email_inboxes[current_prefix] = []
    messages = email_inboxes.get(current_prefix, [])
    response = app.make_response(render_template_string(WEB_TEMPLATE, prefix=current_prefix, emails=messages))
    response.set_cookie('web_prefix', current_prefix, max_age=86400 * 30)
    return response

@app.route('/change')
@app.route('/delete')
def web_reset():
    new_prefix = f"user_{generate_random_prefix()}"
    email_inboxes[new_prefix] = []
    response = redirect(url_for('web_home'))
    response.set_cookie('web_prefix', new_prefix, max_age=86400 * 30)
    return response

# --- TELEGRAM BOT PIPELINE ROUTER ---
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# Permanent bottom-panel grid matching the design mockup layout
def get_telegram_persistent_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_gen = telebot.types.KeyboardButton("➕ Generate New / Delete")
    btn_ref = telebot.types.KeyboardButton("🔄 Refresh")
    markup.add(btn_gen, btn_ref)
    return markup

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda msg: msg.text == "➕ Generate New / Delete")
def tg_handler(message):
    chat_id = message.chat.id
    prefix = f"bot_{generate_random_prefix()}"
    user_emails[chat_id] = prefix
    email_inboxes[prefix] = []
    
    response_msg = (
        f"Your temporary email address:\n\n"
        f"*{prefix}@fixscal.com*\n\n"
        f"[Open in Browser ➡️](https://temp-mail-bot-cbs4.onrender.com)"
    )
    bot.send_message(chat_id, response_msg, parse_mode="Markdown", reply_markup=get_telegram_persistent_keyboard(), disable_web_page_preview=False)

@bot.message_handler(func=lambda msg: msg.text == "🔄 Refresh")
def tg_refresh_handler(message):
    chat_id = message.chat.id
    prefix = user_emails.get(chat_id)
    if not prefix:
        bot.send_message(chat_id, "Please use ➕ Generate New first.", reply_markup=get_telegram_persistent_keyboard())
        return
        
    messages = email_inboxes.get(prefix, [])
    if not messages:
        bot.send_message(chat_id, "📬 *Your inbox is empty*\nWaiting for incoming emails...", parse_mode="Markdown")
    else:
        for mail in messages[-2:]:
            bot.send_message(chat_id, f"📧 **New Email!**\n\n**From:** {mail['sender']}\n**Subject:** {mail['subject']}\n\n{mail['body']}")

# Inbound webhook system connector
@app.route('/email', methods=['POST'])
def receive_email():
    data = request.get_json(silent=True)
    if not data:
        return "No Data Received", 400
    envelope = data.get('envelope', {})
    headers = data.get('headers', {})
    sender = envelope.get('from', 'Unknown Sender')
    subject = headers.get('Subject', 'No Subject')
    body = data.get('plain', 'Empty Body')
    recipient = str(envelope.get('to', '')).lower()
    prefix = recipient.split('@')[0]
    
    email_item = {"sender": sender, "subject": subject, "body": body}
    if prefix not in email_inboxes:
        email_inboxes[prefix] = []
    email_inboxes[prefix].append(email_item)
    
    for chat_id, tg_prefix in list(user_emails.items()):
        if tg_prefix == prefix:
            msg = f"📧 **New Email Received!**\n\n👤 **From:** {sender}\n📌 **Subject:** {subject}\n\n📝 **Message:**\n{body}"
            bot.send_message(chat_id, msg)
            break
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
