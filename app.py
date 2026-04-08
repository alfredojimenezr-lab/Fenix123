from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "fenix123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

sessions = {}

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Error", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True)
    print("Mensaje recibido:", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        user = msg["from"]
        text = msg.get("text", {}).get("body", "").strip().lower()

        response = handle_message(user, text)
        if response:
            send_message(user, response)

    except Exception as e:
        print("Error en webhook:", e)

    return "ok", 200


def handle_message(user, text):
    if user not in sessions:
        sessions[user] = {"step": "menu"}

    session = sessions[user]

    # Reinicio manual: SIEMPRE devuelve menú completo
    if text in ["menu", "menú", "inicio", "hola", "reiniciar"]:
        sessions[user] = {"step": "menu"}
        return menu()

    # ================= MENU =================
    if session["step"] == "menu":
        if text == "1" or text == "filtracion" or text == "filtración" or text == "fuga":
            session["service"] = "filtracion"
            session["step"] = "tipo_propiedad"
            return "Perfecto 👍\n\n¿Es *casa* o *departamento*?"

        if text == "2" or "alcantarill" in text or "olor" in text:
            session["service"] = "alcantarillado"
            session["step"] = "contacto_nombre"
            return "Para alcantarillado u olores se requiere evaluación técnica.\n\nIndícame tu *nombre*."

        if text == "3" or "piscina" in text:
            session["service"] = "piscina"
            session["step"] = "contacto_nombre"
            return "Para piscinas primero realizamos diagnóstico técnico.\n\nIndícame tu *nombre*."

        if text == "4" or "inspeccion" in text or "inspección" in text:
            session["service"] = "inspeccion"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para coordinar la inspección técnica."

        if text == "5" or "seguro" in text or "informe" in text:
            session["service"] = "seguro"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para preparar el informe técnico."

        if text == "6" or "auditoria" in text or "auditoría" in text:
            session["service"] = "auditoria"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para coordinar la auditoría."

        if text == "7" or "otro" in text:
            session["service"] = "otro"
            session["step"] = "contacto_nombre"
            return "Cuéntame tu *nombre* y luego te derivamos con un ejecutivo."

        return menu()

    # ================= FILTRACIÓN =================
    if session.get("service") == "filtracion":

        if session["step"] == "tipo_propiedad":
            if "casa" in text:
                session["tipo"] = "casa"
                session["step"] = "comuna"
                return "¿En qué *comuna* se encuentra? Responde: *Iquique* o *Alto Hospicio*."

            if "depart" in text or "depto" in text or "condominio" in text or "industria" in text:
                session["tipo"] = "no_casa"
                session["step"] = "contacto_nombre"
                return (
                    "🏢 *Evaluación técnica en terreno*\n\n"
                    "En casos de *departamentos, condominios e industrias*, realizamos una *visita técnica sin costo*, ya que las alternativas de detección y localización dependen del sistema interno del edificio, cámaras de alcantarillado, montantes, shafts, bajantes y condiciones estructurales.\n\n"
                    "Coordinemos una *visita técnica gratuita* para evaluar las alternativas de localización y reparación.\n\n"
                    "Luego de la inspección generamos la *cotización oficial* con alcances del servicio, condiciones de pago y garantías.\n\n"
                    "Indícame tu *nombre*."
                )

            return "Por favor responde si es *casa* o *departamento*."

        if session["step"] == "comuna":
            session["comuna"] = text
            session["step"] = "m2"
            return "¿Cuántos *m² aproximados* tiene la propiedad? Responde solo con el número."

        if session["step"] == "m2":
            try:
                session["m2"] = int("".join(filter(str.isdigit, text)))
            except Exception:
                return "Indica solo el número de *m²*."
            session["step"] = "banos"
            return "¿Cuántos *baños* tiene la propiedad? Responde solo con el número."

        if session["step"] == "banos":
            try:
                session["banos"] = int("".join(filter(str.isdigit, text)))
            except Exception:
                return "Indica solo el número de *baños*."
            session["step"] = "ampliacion"
            return "¿La propiedad tiene *ampliaciones*? Responde *sí* o *no*."

        if session["step"] == "ampliacion":
            if text in ["sí", "si", "s"]:
                session["ampliacion"] = True
            elif text in ["no", "n"]:
                session["ampliacion"] = False
            else:
                return "Por favor responde *sí* o *no*."
            session["step"] = "seguro"
            return "¿Requiere *informe para seguro*? Responde *sí* o *no*."

        if session["step"] == "seguro":
            if text in ["sí", "si", "s"]:
                session["seguro"] = True
            elif text in ["no", "n"]:
                session["seguro"] = False
            else:
                return "Por favor responde *sí* o *no*."
            session["step"] = "nombre"
            return "Perfecto. Indícame tu *nombre*."

        if session["step"] == "nombre":
            session["nombre"] = text.title()
            session["step"] = "telefono"
            return "Indícame tu *teléfono de contacto*."

        if session["step"] == "telefono":
            session["telefono"] = text
            session["step"] = "correo"
            return "Indícame tu *correo electrónico*."

        if session["step"] == "correo":
            session["correo"] = text
            session["step"] = "fin"
            return calcular_cotizacion(session)

    # ================= CONTACTO GENERAL =================
    if session["step"] == "contacto_nombre":
        session["nombre"] = text.title()
        session["step"] = "contacto_telefono"
        return "Indícame tu *teléfono*."

    if session["step"] == "contacto_telefono":
        session["telefono"] = text
        session["step"] = "fin"
        return (
            "Gracias 👍\n\n"
            f"Nombre: {session.get('nombre')}\n"
            f"Teléfono: {session.get('telefono')}\n\n"
            "Tu solicitud fue registrada. Un ejecutivo te contactará."
        )

    if session["step"] == "fin":
        return "Tu solicitud ya fue registrada. Si deseas comenzar de nuevo, escribe *inicio*."

    return menu()


def menu():
    return (
        "Hola 👋 Soy *FÉNIX – Detección de Fugas*\n\n"
        "Servicios disponibles:\n"
        "1️⃣ Filtración agua potable\n"
        "2️⃣ Alcantarillado / olores\n"
        "3️⃣ Piscinas\n"
        "4️⃣ Inspección técnica\n"
        "5️⃣ Informe para seguros\n"
        "6️⃣ Auditoría técnica\n"
        "7️⃣ Otro\n\n"
        "Responde con el *número* de la opción o escribe tu problema."
    )


def calcular_cotizacion(s):
    base = 270000

    comuna = s.get("comuna", "").lower()
    m2 = s.get("m2", 0)
    banos = s.get("banos", 1)
    ampliacion = s.get("ampliacion", False)
    seguro = s.get("seguro", False)

    if "hospicio" in comuna:
        base += 40000

    if m2 <= 100:
        factor = 1.0
    elif m2 <= 150:
        factor = 1.0
    elif m2 <= 200:
        factor = 1.3
    elif m2 <= 300:
        factor = 2.0
    else:
        factor = 2.5

    if banos > 1:
        factor += (banos - 1) * 0.1

    if ampliacion:
        factor += 0.2

    precio_servicio = int(base * factor)
    total = precio_servicio + (60000 if seguro else 0)

    enviar_correo(s, precio_servicio, total)

    respuesta = (
        "💧 *Cotización estimada*\n\n"
        f"💰 Servicio: CLP {precio_servicio:,}".replace(",", ".") +
        "\n"
    )

    if seguro:
        respuesta += "📄 Informe para seguro: CLP 60.000\n"
        respuesta += f"\n💵 Total: CLP {total:,}".replace(",", ".")

    respuesta += (
        "\n\n"
        f"Nombre: {s['nombre']}\n"
        f"Teléfono: {s['telefono']}\n\n"
        "Indícanos si estás de acuerdo para generar la *cotización oficial* con los alcances del servicio, condiciones de pago, garantías y agendar el inicio del servicio.\n"
        "Contamos con todos los medios de pago disponibles."
    )

    return respuesta


def enviar_correo(s, precio_servicio, total):
    try:
        remitente = os.environ.get("EMAIL_REMITENTE")
        clave = os.environ.get("EMAIL_PASSWORD_APP")
        destino = os.environ.get("EMAIL_DESTINO")

        if not remitente or not clave or not destino:
            print("Error correo: faltan variables EMAIL_REMITENTE, EMAIL_PASSWORD_APP o EMAIL_DESTINO")
            return

        asunto = "Nuevo cliente - Fenix Bot"

        mensaje = f"""
Nuevo cliente ingresado:

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Servicio: {s.get('service')}
Tipo: {s.get('tipo')}
Comuna: {s.get('comuna')}
Superficie: {s.get('m2')} m2
Baños: {s.get('banos')}
Ampliaciones: {"Sí" if s.get("ampliacion") else "No"}

Informe para seguro: {"Sí" if s.get("seguro") else "No"}
Valor servicio: CLP {precio_servicio}
Total: CLP {total}
"""

        msg = MIMEText(mensaje, "plain", "utf-8")
        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destino

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(remitente, clave)
        server.send_message(msg)
        server.quit()

        print("✅ Correo enviado correctamente")

    except Exception as e:
        print("❌ Error enviando correo:", e)


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

    response = requests.post(url, json=payload, headers=headers)
    print("Respuesta enviada:", response.text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
