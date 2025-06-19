import requests

BOT_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
CHAT_ID = "012345678"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)
    print(f"Sent message to Telegram: {text}")
