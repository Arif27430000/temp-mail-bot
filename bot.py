import os
import random
import string
import telebot
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# System Configurations
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Persistent In-Memory Databases
user_emails = {}   # Maps chat_id -> "assigned_prefix"
email_inboxes = {} # Maps "assigned_prefix" -> [list of emails]

def generate_random_prefix(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# ---------------------------------------------------
# 1. PREMIUM WEB INTERFACE LAYOUT (Matching temp-mail.org)
# ---------------------------------------------------
WEB_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Temp Mail - Disposable Temporary Email</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #171d2b; color: #f8fafc; margin:0; padding:0; }
        .header { background-color: #1e2640; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; }
        .logo { color: #00e676; font-size: 22px; font-weight: bold; letter-spacing: 1px; }
        .container { max-width: 550px; margin: 30px auto; padding: 0 20px; text-align: center; }
        h1 { font-size: 24px; margin-bottom: 20px; color: #ffffff; font-weight: 600; }
        .email-box { background: #242f4d; padding: 15px; border-radius: 8px; border: 2px dashed #3a4b7c; font-size: 18px; margin-bottom: 20px; word-break: break-all; color: #00e676; font-weight: bold; }
        .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 30px; }
        .btn { background: #2d3a60; color: white; padding: 12px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; font-size: 14px; display: flex; align-items: center; justify-content: center; }
        .btn:hover { background: #3a4b7c; }
        .btn-green { background: #00e676; color: #171d2b; }
        .btn-green:hover { background: #00c853; }
        .inbox-card { background: #1e2640; border-radius: 8px; padding: 20px; text-align: left; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .inbox-header { font-size: 16px; font-weight: bold; border-bottom: 1px solid #3a4b7c; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; color: #94a3b8; }
        .email-item { background: #242f4d; padding: 15px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #00e676; }
        .email-meta { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
        .email-subject { font-weight: bold; font-size: 15px; margin-bottom: 5px; color: #ffffff; }
        .email-body { font-size: 14px; color: #cbd5e1; white-space: pre-wrap; }
        .empty-state { text-align: center; padding: 40px 20px; color: #94a3b8; }
        .empty-icon { font-size: 48px; margin-bottom: 15px; display:block; color: #3a4b7c; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🔒 TEMP MAIL</div>
    </div>
    <div class="container">
        <h1>Your Temporary Email Address</h1>
        <div class="email-box">{{ prefix }}@fixscal.com</div>
        
        <div class="actions">
            <button class="btn btn-green" onclick="navigator.clipboard.writeText('{{ prefix }}@fixscal.com'); alert('Copied to clipboard!');">Copy</button>
            <a href="/" class="btn">Refresh</a>
            <a href="/change" class="btn">Change</a>
            <a href="/delete" class="btn" style="color: #ff5252;">Delete</a>
        </div>

        <div class="inbox-card">
            <div class="inbox-header">
                <span>INBOX</span>
                <span style="font-size: 12px; color: #00e676;">Waiting for incoming messages...</span>
            </div>
            
            {% if emails %}
                {% for mail in emails %}
                    <div class="email-item">
                        <div class="email-meta">From: {{ mail.sender }}</div>
                        <div class="email-subject">Subject: {{ mail.subject }}</div>
                        <div class="email-body">{{ mail.body }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <span class="empty-icon">✉️</span>
                    Your inbox is empty<br>
                    <span style="font-size: 12px; color: #64748b;">Waiting for incoming emails</span>
                </div>
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

# ---------------------------------------------------
# 2. TELEGRAM INTERFACE PIPELINE (Matching Telegram Layout)
# ---------------------------------------------------
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

def make_telegram_keyboard():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_gen = telebot.types.InlineKeyboardButton("➕ Generate New / Delete", callback_data="tg_generate")
    btn_ref = telebot.types.InlineKeyboardButton("🔄 Refresh", callback_data="tg_refresh")
    markup.add(btn_gen, btn_ref)
    return markup

@bot.message_handler(commands=['start'])
def tg_start(message):
    chat_id = message.chat.id
    
    if chat_id not in user_emails:
        prefix = f"bot_{generate_random_prefix()}"
        user_emails[chat_id] = prefix
        email_inboxes[prefix] = []
    else:
        prefix = user_emails[chat_id]

    msg_text = f"Your temporary email address:\n\n`{prefix}@fixscal.com`\n\n[Open in Browser ➡️](https://temp-mail-bot-cbs4.onrender.com)"
    bot.send_message(chat_id, msg_text, parse_mode="Markdown", reply_markup=make_telegram_keyboard())

@bot.callback_query_handler(func=lambda call: call.data in ["tg_generate", "tg_refresh"])
def handle_tg_buttons(call):
    chat_id = call.message.chat.id
    
    if call.data == "tg_generate":
        prefix = f"bot_{generate_random_prefix()}"
        user_emails[chat_id] = prefix
        email_inboxes[prefix] = []
        
        bot.answer_callback_query(call.id, "New Address Generated!")
        msg_text = f"Your temporary email address:\n\n`{prefix}@fixscal.com`\n\n[Open in Browser ➡️](https://temp-mail-bot-cbs4.onrender.com)"
        bot.edit_message_text(msg_text, chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=make_telegram_keyboard())
        
    elif call.data == "tg_refresh":
        prefix = user_emails.get(chat_id)
        if not prefix:
            bot.answer_callback_query(call.id, "Error: Start the bot first.")
            return
            
        messages = email_inboxes.get(prefix, [])
        bot.answer_callback_query(call.id, f"Refreshed! ({len(messages)} emails)")
        
        for mail in messages[-2:]:  
            bot.send_message(chat_id, f"📧 **New Email Received!**\n\n👤 **From:** {mail['sender']}\n📌 **Subject:** {mail['subject']}\n\n📝 **Message:**\n{mail['body']}")

# ---------------------------------------------------
# 3. CLOUDMAILIN INBOUND WEBHOOK ENDPOINT
# ---------------------------------------------------
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
    
    email_item = {
        "sender": sender,
        "subject": subject,
        "body": body
    }
    
    if prefix not in email_inboxes:
        email_inboxes[prefix] = []
    email_inboxes[prefix].append(email_item)
    
    for chat_id, tg_prefix in user_emails.items():
        if tg_prefix == prefix:
            msg = f"📧 **New Inbound Mail Received!**\n\n👤 **From:** {sender}\n📌 **Subject:** {subject}\n\n📝 **Message:**\n{body}"
            bot.send_message(chat_id, msg)
            break
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

