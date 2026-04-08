from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

VERIFY_TOKEN = "fenix123"

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
def enviar_correo(s, precio):

    try:
        remitente = os.environ.get("EMAIL_USER")
        clave = os.environ.get("EMAIL_PASS")
        destino = os.environ.get("EMAIL_TO")

        mensaje = f"""
Nuevo cliente FÉNIX:

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Servicio: {s.get('servicio')}
Comuna: {s.get('comuna')}
Superficie: {s.get('m2')} m2
Baños: {s.get('banos')}

Seguro: {"Sí" if s.get("seguro") else "No"}

Valor estimado: CLP {precio}
"""

        msg = MIMEText(mensaje)
        msg["Subject"] = "🚨 Nuevo cliente Fenix Bot"
        msg["From"] = remitente
        msg["To"] = destino

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(remitente, clave)
        server.send_message(msg)
        server.quit()

        print("Correo enviado")

    except Exception as e:
        print("Error correo:", e)

# =========================
# CÁLCULO COMPLEJIDAD
# =========================
def calcular_factor(m2, banos, ampliacion):

    if m2 <= 100:
        factor = 1.0
    elif m2 <= 150:
        factor = 1.3
    elif m2 <= 200:
        factor = 2.0
    else:
        factor = 2.5

    factor += (banos - 1) * 0.1

    if ampliacion:
        factor += 0.2

    return factor

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def receive_message():

    data = request.get_json(silent=True)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        text = message["text"]["body"].lower()

        # RESPUESTA SIMPLE (ejemplo demo)
        if "filtracion" in text:

            # DATOS SIMULADOS (luego los conectamos dinámicos)
            s = {
                "nombre": "Cliente",
                "telefono": from_number,
                "correo": "no informado",
                "servicio": "Filtración agua potable",
                "comuna": "Iquique",
                "m2": 220,
                "banos": 3,
                "seguro": True
            }

            factor = calcular_factor(220, 3, False)
            base = 270000
            precio = int(base * factor)

            mensaje = f"""
💧 Cotización estimada:

Valor servicio: CLP {precio}

Valor informe para seguro: CLP 60.000

Indícanos si estás de acuerdo para generar la cotización oficial con los alcances del servicio, condiciones de pago, garantías y agendar el inicio del servicio. Contamos con todos los medios de pago disponibles.
"""

            send_whatsapp_message(from_number, mensaje)
            enviar_correo(s, precio)

        else:
            send_whatsapp_message(from_number, "Hola 👋 Soy Fénix Bot. ¿En qué puedo ayudarte?")

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED", 200
