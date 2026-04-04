from flask import Flask, request

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
    return "EVENT_RECEIVED", 200
