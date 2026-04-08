from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = "fenix123"

@app.route("/")
def home():
    return "Bot activo", 200

@app.route("/health")
def health():
    return "ok", 200

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Token inválido", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True)
    print("Mensaje recibido:", data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]

        send_whatsapp_message(from_number, "Hola 👋 soy Fenix Bot. ¿En qué puedo ayudarte?")

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED", 200


def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{os.environ.get('PHONE_NUMBER_ID')}/messages"

    headers = {
        "Authorization": f"Bearer {os.environ.get('WHATSAPP_TOKEN')}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": text
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    print("Respuesta enviada:", response.text)
