from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

VERIFY_TOKEN = "fenix123"

# =========================
# VARIABLES
# =========================
user_states = {}

BASE_PRICE = 250000
FACTOR_AMPLIACION = 0.4
VALOR_INFORME = 50000

# =========================
# ENVÍO WHATSAPP
# =========================
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
        "text": {"body": text}
    }

    requests.post(url, json=payload, headers=headers)

# =========================
# ENVÍO CORREO
# =========================
def send_email(subject, body):
    try:
        sender = os.environ.get("EMAIL_USER")
        password = os.environ.get("EMAIL_PASS")

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = sender

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender, password)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Error correo:", e)

# =========================
# CÁLCULO FACTOR
# =========================
def calcular_factor(m2, banos, ampliacion):

    if m2 <= 100:
        factor = 1.0
    elif m2 <= 150:
        factor = 1.5
    elif m2 <= 200:
        factor = 2.0
    elif m2 <= 250:
        factor = 2.5
    elif m2 <= 300:
        factor = 3.0
    elif m2 <= 350:
        factor = 3.5
    else:
        return None

    factor += (banos - 1) * 0.1

    if ampliacion:
        factor += FACTOR_AMPLIACION

    return factor

# =========================
# WEBHOOK VERIFY
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Error", 403

# =========================
# WEBHOOK RECEIVE
# =========================
@app.route("/webhook", methods=["POST"])
def receive():
    data = request.get_json()
    print("DATA:", data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        incoming = message["text"]["body"].lower()
    except:
        return "ok", 200

    state = user_states.get(from_number, {})

    # =========================
    # INICIO
    # =========================
    if from_number not in user_states:

        user_states[from_number] = {"step": "menu"}

        send_whatsapp_message(from_number,
            "Hola 👋 soy *Fenix Bot*\n\n"
            "¿En qué puedo ayudarte?\n\n"
            "1️⃣ Filtración en casa\n"
            "2️⃣ Departamento / Condominio\n"
            "3️⃣ Piscina\n"
            "4️⃣ Alcantarillado\n"
            "5️⃣ Otro servicio"
        )
        return "ok", 200

    # =========================
    # MENÚ
    # =========================
    if state["step"] == "menu":

        if "1" in incoming:
            state["step"] = "casa_m2"
            state["tipo"] = "casa"

            send_whatsapp_message(from_number, "Indícame los m² de la casa")

        elif incoming in ["2","3","4","5"]:
            state["step"] = "agenda_visita"
            state["tipo"] = "visita"

            send_whatsapp_message(from_number,
                "Para poder ayudarte correctamente, necesitamos una visita técnica.\n\n"
                "Indícame:\n📅 Día\n🕒 Bloque (mañana o tarde)"
            )

        user_states[from_number] = state
        return "ok", 200

    # =========================
    # CASA → CÁLCULO
    # =========================
    if state["step"] == "casa_m2":
        state["m2"] = int(incoming)
        state["step"] = "casa_banos"
        send_whatsapp_message(from_number, "¿Cuántos baños tiene?")
        return "ok", 200

    if state["step"] == "casa_banos":
        state["banos"] = int(incoming)
        state["step"] = "casa_amp"
        send_whatsapp_message(from_number, "¿Tiene ampliaciones? (si/no)")
        return "ok", 200

    if state["step"] == "casa_amp":
        state["amp"] = "si" in incoming

        factor = calcular_factor(state["m2"], state["banos"], state["amp"])

        if factor is None:
            send_whatsapp_message(from_number,
                "Para esta propiedad se requiere visita técnica sin costo.\n\n"
                "Indícame día para agendar."
            )
            state["step"] = "agenda_dia"
            return "ok", 200

        precio = int(BASE_PRICE * factor)

        state["precio"] = precio
        state["step"] = "seguro"

        send_whatsapp_message(from_number,
            f"💰 Valor estimado: ${precio:,}\n\n"
            "Este valor incluye localización de la filtración y reparación.\n\n"
            "¿Necesitas informe para seguro? (si/no)"
        )
        return "ok", 200

    if state["step"] == "seguro":

        if "si" in incoming:
            state["precio"] += VALOR_INFORME

        state["step"] = "acepta"

        send_whatsapp_message(from_number,
            f"💰 Valor final estimado: ${state['precio']:,}\n\n"
            "¿Deseas avanzar con el servicio? (si/no)"
        )
        return "ok", 200

    if state["step"] == "acepta":

        if "si" in incoming:

            send_email(
                "Cliente aceptó cotización",
                f"Tel: {from_number}\nPrecio: {state['precio']}"
            )

            state["step"] = "agenda_dia"

            send_whatsapp_message(from_number,
                "Perfecto 👍\n\nIndícame qué día te acomoda."
            )

        else:
            send_whatsapp_message(from_number,
                "Perfecto, quedamos atentos si necesitas ayuda."
            )
            user_states.pop(from_number)

        return "ok", 200

    # =========================
    # AGENDA CASA
    # =========================
    if state["step"] == "agenda_dia":

        send_email(
            "Nueva visita casa",
            f"Tel: {from_number}\nDía: {incoming}\nPrecio: {state.get('precio')}"
        )

        send_whatsapp_message(from_number,
            f"✅ Visita agendada para el día {incoming}\n\n"
            "Te contactaremos para confirmar."
        )

        user_states.pop(from_number)
        return "ok", 200

    # =========================
    # VISITA TÉCNICA
    # =========================
    if state["step"] == "agenda_visita":

        state["agenda"] = incoming

        send_email(
            "Nueva visita técnica",
            f"Tel: {from_number}\nAgenda: {incoming}"
        )

        send_whatsapp_message(from_number,
            "✅ Visita solicitada correctamente.\n\n"
            "Te contactaremos para confirmar."
        )

        user_states.pop(from_number)
        return "ok", 200

    return "ok", 200

@app.route("/")
def home():
    return "Bot activo", 200
