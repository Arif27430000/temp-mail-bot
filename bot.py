import os
import random
import string
import requests
import telebot
from threading import Thread
import time

# Direct Bot Token Configuration
TOKEN = "8953590306:AAFfDTe3BxPnp0PhogapywtSzSeWPPmobjo"
bot = telebot.TeleBot(TOKEN)

API_URL = "https://api.mail.tm"

# In-Memory Session Database
# Maps chat_id -> {'address': '...', 'token': '...', 'last_checked': ...}
user_accounts = {}

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_bot_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_rand = telebot.types.KeyboardButton("🎲 random")
    btn_change = telebot.types.KeyboardButton("➕ change")
    btn_ref = telebot.types.KeyboardButton("🔄 refresh")
    btn_del = telebot.types.KeyboardButton("🗑️ delete")
    markup.add(btn_rand, btn_change)
    markup.add(btn_ref, btn_del)
    return markup

# Helper function to create an account through the free API network
def create_mail_tm_account(chat_id):
    try:
        # 1. Fetch available public domains
        dom_res = requests.get(f"{API_URL}/domains").json()
        domain = dom_res['hydra:member'][0]['domain']
        
        # 2. Register a randomized username address profile
        prefix = generate_random_string(10)
        email_str = f"{prefix}@{domain}"
        password_str = generate_random_string(12)
        
        acc_payload = {"address": email_str, "password": password_str}
        acc_res = requests.post(f"{API_URL}/accounts", json=acc_payload)
        
        if acc_res.status_code == 201:
            # 3. Request a session JWT token
            tok_res = requests.post(f"{API_URL}/token", json=acc_payload).json()
            user_accounts[chat_id] = {
                "address": email_str,
                "token": tok_res['token']
            }
            return email_str
    except Exception as e:
        print(f"Account Generation Error: {e}")
    return None

# Background mail checking loop to push messages to Telegram instantly
def automatic_mail_checker():
    while True:
        for chat_id, account in list(user_accounts.items()):
            try:
                headers = {"Authorization": f"Bearer {account['token']}"}
                msg_res = requests.get(f"{API_URL}/messages", headers=headers).json()
                emails = msg_res.get('hydra:member', [])
                
                for mail in emails:
                    # Fetch single full message details
                    mail_id = mail['id']
                    detail_res = requests.get(f"{API_URL}/messages/{mail_id}", headers=headers).json()
                    
                    # Extract plaintext text content body
                    body_content = detail_res.get('text', 'Empty Body Message')
                    sender = detail_res['from']['address']
                    subject = detail_res.get('subject', 'No Subject')
                    
                    # Send alert to Telegram user channel
                    alert = (
                        f"📧 **New Mail Received!**\n\n"
                        f"👤 **From:** {sender}\n"
                        f"📌 **Subject:** {subject}\n\n"
                        f"📝 **Message:**\n{body_content}"
                    )
                    bot.send_message(chat_id, alert, parse_mode="Markdown")
                    
                    # Delete message from the remote temporary storage server so it doesn't trigger again
                    requests.delete(f"{API_URL}/messages/{mail_id}", headers=headers)
            except Exception as e:
                pass
        time.sleep(5)  # Poll the open endpoints every 5 seconds for new emails

@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    bot.send_message(message.chat.id, "🔄 Generating your free temporary mailbox address. Please wait...")
    
    email_address = create_mail_tm_account(chat_id)
    if email_address:
        msg = f"✨ **Free Temporary Email Active**\n\nYour address is:\n`{email_address}`\n\nAny incoming messages will print here immediately!"
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=get_bot_keyboard())
    else:
        bot.send_message(chat_id, "❌ Network busy. Please press /start to try again.")

@bot.message_handler(func=lambda msg: msg.text in ["🎲 random", "➕ change"])
def change_cmd(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "🔄 Generating a new random email address...")
    email_address = create_mail_tm_account(chat_id)
    if email_address:
        msg = f"✨ **New Address Generated:**\n`{email_address}`"
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=get_bot_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🔄 refresh")
def refresh_cmd(message):
    chat_id = message.chat.id
    account = user_accounts.get(chat_id)
    if not account:
        bot.send_message(chat_id, "No active mailbox. Tap 🎲 random to start.")
        return
        
    bot.send_message(chat_id, "Checking for incoming messages... 🔍")
    # The automatic background thread handles delivery, but this provides instant visual response

@bot.message_handler(func=lambda msg: msg.text == "🗑️ delete")
def delete_cmd(message):
    chat_id = message.chat.id
    if chat_id in user_accounts:
        del user_accounts[chat_id]
    bot.send_message(message.chat.id, "🗑️ Current address deleted. Your inbox is closed.", reply_markup=get_bot_keyboard())

if __name__ == '__main__':
    # Initialize background worker loop thread
    check_thread = Thread(target=automatic_mail_checker, daemon=True)
    check_thread.start()
    
    # Run Telegram Polling Engine natively
    bot.infinity_polling()
