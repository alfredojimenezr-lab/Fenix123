from flask import Flask, request
import os
import requests
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "fenix123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE", "")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "alfredo.jimenez@tengounafuga.cl")
EMAIL_PASSWORD_APP = os.getenv("EMAIL_PASSWORD_APP", "")

usuarios = {}


def enviar(numero, mensaje):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=data, timeout=20)


def enviar_correo(data):
    if not EMAIL_REMITENTE or not EMAIL_PASSWORD_APP or not EMAIL_DESTINO:
        return

    mensaje = f"""
Nuevo cliente BOT FENIX

Nombre: {data.get("nombre")}
Telefono: {data.get("telefono")}
Servicio: {data.get("servicio")}
Comuna: {data.get("comuna")}
Direccion: {data.get("direccion")}
Correo: {data.get("correo")}
"""

    msg = MIMEText(mensaje)
    msg["Subject"] = "Nuevo cliente BOT FENIX"
    msg["From"] = EMAIL_REMITENTE
    msg["To"] = EMAIL_DESTINO

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_REMITENTE, EMAIL_PASSWORD_APP)
    server.sendmail(EMAIL_REMITENTE, EMAIL_DESTINO, msg.as_string())
    server.quit()


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


@app.route("/webhook", methods=["GET"])
def verificar():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", "")
    return "error", 403


@app.route("/webhook", methods=["POST"])
def responder():
    data = request.json or {}

    try:
        numero = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
        texto = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"].strip()

        if numero not in usuarios:
            usuarios[numero] = {"estado": "inicio"}

        estado = usuarios[numero]["estado"]

        if estado == "inicio":
            enviar(
                numero,
                "Hola 👋 FÉNIX\n\n"
                "1️⃣ Agua potable\n"
                "2️⃣ Alcantarillado\n"
                "3️⃣ Piscinas\n"
                "4️⃣ Auditoría"
            )
            usuarios[numero]["estado"] = "servicio"

        elif estado == "servicio":
            servicios = {
                "1": "Agua potable",
                "2": "Alcantarillado",
                "3": "Piscinas",
                "4": "Auditoría"
            }
            usuarios[numero]["servicio"] = servicios.get(texto, "Otro")
            enviar(numero, "Nombre completo:")
            usuarios[numero]["estado"] = "nombre"

        elif estado == "nombre":
            usuarios[numero]["nombre"] = texto
            enviar(numero, "Teléfono:")
            usuarios[numero]["estado"] = "telefono"

        elif estado == "telefono":
            usuarios[numero]["telefono"] = texto
            enviar(numero, "Comuna:")
            usuarios[numero]["estado"] = "comuna"

        elif estado == "comuna":
            usuarios[numero]["comuna"] = texto.lower()
            enviar(numero, "Dirección:")
            usuarios[numero]["estado"] = "direccion"

        elif estado == "direccion":
            usuarios[numero]["direccion"] = texto
            enviar(numero, "Correo:")
            usuarios[numero]["estado"] = "correo"

        elif estado == "correo":
            usuarios[numero]["correo"] = texto

            if usuarios[numero]["servicio"] == "Agua potable":
                enviar(numero, "Tipo de inmueble:\n1 Casa\n2 Departamento")
                usuarios[numero]["estado"] = "tipo"
            else:
                enviar(
                    numero,
                    "Se requiere visita técnica sin costo.\n\n"
                    "Te contactaremos para coordinar."
                )
                enviar_correo(usuarios[numero])
                usuarios[numero]["estado"] = "fin"

        elif estado == "tipo":
            if texto == "1":
                usuarios[numero]["tipo"] = "casa"
                enviar(numero, "Metros cuadrados:")
                usuarios[numero]["estado"] = "m2"
            else:
                enviar(
                    numero,
                    "Se requiere visita técnica sin costo.\n\n"
                    "Te contactaremos para coordinar."
                )
                enviar_correo(usuarios[numero])
                usuarios[numero]["estado"] = "fin"

        elif estado == "m2":
            usuarios[numero]["m2"] = int(texto)
            enviar(numero, "Cantidad de baños:")
            usuarios[numero]["estado"] = "banos"

        elif estado == "banos":
            usuarios[numero]["banos"] = int(texto)
            enviar(numero, "¿Tiene ampliaciones?\n1 Sí\n2 No")
            usuarios[numero]["estado"] = "amp"

        elif estado == "amp":
            usuarios[numero]["amp"] = texto

            base = 270000
            factor = 1.0

            if usuarios[numero]["m2"] > 80:
                factor = 1.5
            if usuarios[numero]["banos"] >= 2:
                factor = max(factor, 1.5)
            if texto == "1":
                factor = 2.0

            precio = int(base * factor)

            if "alto hospicio" in usuarios[numero]["comuna"]:
                precio += 40000

            enviar(numero, f"💰 Total estimado: ${precio:,} + IVA".replace(",", "."))
            enviar(
                numero,
                "Indícanos si estás de acuerdo para generar la cotización oficial con los alcances del servicio, "
                "condiciones de pago, garantías y agendar el inicio del servicio. "
                "También disponemos de todo medio de pago."
            )

            enviar_correo(usuarios[numero])
            usuarios[numero]["estado"] = "fin"

    except Exception:
        pass

    return "ok", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)