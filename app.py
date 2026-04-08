from flask import Flask, request
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "fenix123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

sessions = {}

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True)
    print("Mensaje:", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        user = msg["from"]
        text = msg.get("text", {}).get("body", "").lower()

        response = handle_message(user, text)
        send_message(user, response)

    except Exception as e:
        print("Error:", e)

    return "ok", 200


# =========================
# LÓGICA PRINCIPAL
# =========================

def handle_message(user, text):

    if user not in sessions:
        sessions[user] = {"step": "menu"}

    session = sessions[user]

    # RESET
    if text in ["menu", "inicio", "hola"]:
        session["step"] = "menu"
        return menu()

    # ================= MENU =================
    if session["step"] == "menu":

        if "1" in text or "filtr" in text:
            session["service"] = "filtracion"
            session["step"] = "tipo_propiedad"
            return "Perfecto 👍\n\n¿Es casa o departamento?"

        if "2" in text:
            session["step"] = "contacto"
            return "Para alcantarillado necesitamos evaluación técnica.\n\nIndícame tu nombre."

        if "3" in text:
            session["step"] = "contacto"
            return "Para piscinas realizamos diagnóstico.\n\nIndícame tu nombre."

        if "4" in text:
            session["step"] = "contacto"
            return "Indícame tu nombre para inspección técnica."

        if "5" in text:
            session["step"] = "contacto"
            return "Indícame tu nombre para informe técnico."

        if "6" in text:
            session["step"] = "contacto"
            return "Indícame tu nombre para auditoría."

        if "7" in text:
            session["step"] = "contacto"
            return "Cuéntame tu nombre y el problema."

        return menu()

    # ================= FILTRACIÓN =================
    if session.get("service") == "filtracion":

        if session["step"] == "tipo_propiedad":

            if "casa" in text:
                session["tipo"] = "casa"
                session["step"] = "comuna"
                return "¿En qué comuna? (Iquique / Alto Hospicio)"

            else:
                session["step"] = "contacto"
                return "Para departamentos o industrias realizamos visita técnica.\n\nIndícame tu nombre."

        if session["step"] == "comuna":

            session["comuna"] = text
            session["step"] = "m2"
            return "¿Cuántos m² aprox?"

        if session["step"] == "m2":

            try:
                session["m2"] = int(''.join(filter(str.isdigit, text)))
            except:
                return "Indica solo el número de m²."

            session["step"] = "banos"
            return "¿Cuántos baños?"

        if session["step"] == "banos":

            try:
                session["banos"] = int(''.join(filter(str.isdigit, text)))
            except:
                return "Indica número de baños."

            session["step"] = "ampliacion"
            return "¿Tiene ampliaciones? (sí/no)"

        if session["step"] == "ampliacion":

            session["ampliacion"] = "si" in text
            session["step"] = "seguro"
            return "¿Requiere informe para seguro? (sí/no)"

        if session["step"] == "seguro":

            session["seguro"] = "si" in text
            session["step"] = "nombre"
            return "Indícame tu nombre."

        if session["step"] == "nombre":

            session["nombre"] = text
            session["step"] = "telefono"
            return "Tu teléfono de contacto."

        if session["step"] == "telefono":

            session["telefono"] = text
            session["step"] = "correo"
            return "Tu correo electrónico."

        if session["step"] == "correo":

            session["correo"] = text
            session["step"] = "fin"

            return calcular_cotizacion(session)

    # ================= CONTACTO GENERAL =================
    if session["step"] == "contacto":

        session["nombre"] = text
        session["step"] = "telefono"
        return "Indícame tu teléfono."

    if session["step"] == "telefono":

        session["telefono"] = text
        session["step"] = "fin"
        return "Gracias 👍 Un ejecutivo te contactará."

    if session["step"] == "fin":
        return "Tu solicitud ya fue registrada."

    return menu()


# =========================
# MENÚ
# =========================

def menu():
    return (
        "Hola 👋 Soy *FÉNIX – Detección de Fugas*\n\n"
        "Servicios:\n"
        "1️⃣ Filtración agua potable\n"
        "2️⃣ Alcantarillado\n"
        "3️⃣ Piscinas\n"
        "4️⃣ Inspección técnica\n"
        "5️⃣ Informe para seguros\n"
        "6️⃣ Auditoría técnica\n"
        "7️⃣ Otro\n\n"
        "Responde con el número."
    )


# =========================
# COTIZACIÓN
# =========================

def calcular_cotizacion(s):

    if s["m2"] > 80 or s["banos"] > 1 or s["ampliacion"]:
        return (
            "Este caso requiere visita técnica.\n\n"
            f"Nombre: {s['nombre']}\n"
            f"Teléfono: {s['telefono']}\n"
            "Te contactaremos."
        )

    precio = 270000

    if "hospicio" in s["comuna"]:
        precio += 40000

    if s["seguro"]:
        precio += 60000

    return (
        "💧 Cotización estimada:\n\n"
        f"💰 CLP {precio:,}".replace(",", ".") +
        "\n\nIncluye detección de filtración.\n"
        f"Nombre: {s['nombre']}\n"
        f"Teléfono: {s['telefono']}"
    )


# =========================
# ENVÍO
# =========================

def send_message(to, text):

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    requests.post(url, json=payload, headers=headers)
