from flask import Flask, request
import requests
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "fenix123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

sessions = {}


# =========================
# UTILIDADES
# =========================

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def es_aceptacion(texto):
    texto = texto.lower().strip()
    afirmativos = [
        "si", "sí", "ok", "de acuerdo", "acepto", "aceptar",
        "conforme", "me parece", "quiero agendar", "agendar",
        "avancemos", "adelante", "confirmo", "confirmar"
    ]
    return any(a in texto for a in afirmativos)


def detectar_servicio(texto):
    texto = texto.lower()

    if any(p in texto for p in [
        "filtracion", "filtración", "fuga", "goteo", "pierde agua",
        "humedad", "mojado", "mancha", "agua en muro", "agua en piso",
        "filtra agua", "fuga de agua"
    ]):
        return "filtracion"

    if any(p in texto for p in [
        "olor", "hedor", "alcantarillado", "desagüe", "desague",
        "mal olor", "olor a desague", "olor a alcantarillado"
    ]):
        return "alcantarillado"

    if any(p in texto for p in [
        "piscina", "agua verde", "agua turbia", "cloro", "ph",
        "bomba piscina", "filtro piscina"
    ]):
        return "piscina"

    if any(p in texto for p in [
        "seguro", "informe", "aseguradora", "liquidacion", "liquidación"
    ]):
        return "seguro"

    if any(p in texto for p in [
        "revision", "revisión", "inspeccion", "inspección",
        "evaluacion", "evaluación", "auditoria", "auditoría"
    ]):
        return "inspeccion"

    return None


# =========================
# CORREO
# =========================

def enviar_correo_generico(asunto, cuerpo):
    try:
        remitente = os.environ.get("EMAIL_REMITENTE")
        clave = os.environ.get("EMAIL_PASSWORD_APP")
        destino = os.environ.get("EMAIL_DESTINO")

        if not remitente or not clave or not destino:
            print("❌ Faltan variables EMAIL_REMITENTE, EMAIL_PASSWORD_APP o EMAIL_DESTINO")
            return

        msg = MIMEText(cuerpo, "plain", "utf-8")
        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destino

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(remitente, clave)
        server.send_message(msg)
        server.quit()

        print("✅ Correo enviado correctamente:", asunto)

    except Exception as e:
        print("❌ Error enviando correo:", e)


def enviar_correo_cotizacion(s, precio_servicio, total):
    cuerpo = f"""
Nueva cotización registrada

Fecha: {ahora()}

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Servicio: {s.get('service')}
Tipo propiedad: {s.get('tipo')}
Comuna: {s.get('comuna')}
Superficie: {s.get('m2')} m2
Baños: {s.get('banos')}
Ampliaciones: {"Sí" if s.get("ampliacion") else "No"}

Informe para seguro: {"Sí" if s.get("seguro") else "No"}
Valor servicio: CLP {precio_servicio:,}
Total: CLP {total:,}
""".replace(",", ".")

    enviar_correo_generico("Nueva cotización - Fenix Bot", cuerpo)


def enviar_correo_aceptacion(s):
    cuerpo = f"""
Cliente acepta valor estimado

Fecha: {ahora()}

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Servicio: {s.get('service')}
Tipo propiedad: {s.get('tipo')}
Comuna: {s.get('comuna')}
Superficie: {s.get('m2')} m2
Baños: {s.get('banos')}
Ampliaciones: {"Sí" if s.get("ampliacion") else "No"}

Informe para seguro: {"Sí" if s.get("seguro") else "No"}
Valor servicio: CLP {s.get('precio_servicio', 0):,}
Total: CLP {s.get('total', 0):,}
""".replace(",", ".")

    enviar_correo_generico("Cliente aceptó valor estimado - Fenix Bot", cuerpo)


def enviar_correo_interaccion(user, direccion, texto, session=None):
    cuerpo = f"""
Interacción registrada

Fecha: {ahora()}
Número: {user}
Dirección: {direccion}

Mensaje:
{texto}
"""

    if session:
        cuerpo += f"""

Contexto actual:
step: {session.get('step')}
service: {session.get('service')}
tipo: {session.get('tipo')}
nombre: {session.get('nombre')}
telefono: {session.get('telefono')}
correo: {session.get('correo')}
comuna: {session.get('comuna')}
m2: {session.get('m2')}
banos: {session.get('banos')}
seguro: {session.get('seguro')}
"""

    enviar_correo_generico(f"Interacción WhatsApp - {direccion}", cuerpo)


# =========================
# WHATSAPP
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

    response = requests.post(url, json=payload, headers=headers)
    print("Respuesta enviada:", response.text)

    # registrar interacción saliente
    enviar_correo_interaccion(to, "BOT → CLIENTE", text)


# =========================
# MENÚ
# =========================

def menu():
    return (
        "Hola 👋 Soy *FÉNIX – Especialistas en detección de fugas*\n\n"
        "💧 Detectamos filtraciones sin romper de más\n"
        "📍 Atención en Iquique y Alto Hospicio\n\n"
        "Indica tu problema o selecciona una opción:\n\n"
        "1️⃣ Filtración de agua potable\n"
        "2️⃣ Olor / alcantarillado\n"
        "3️⃣ Problemas en piscina\n"
        "4️⃣ Inspección técnica\n"
        "5️⃣ Informe para seguro\n"
        "6️⃣ Auditoría técnica\n"
        "7️⃣ Otro\n\n"
        "Responde con el número o describe tu problema."
    )


# =========================
# CÁLCULO COTIZACIÓN
# =========================

def calcular_cotizacion(s):
    base = 270000

    comuna = s.get("comuna", "").lower()
    m2 = s.get("m2", 0)
    banos = s.get("banos", 1)
    ampliacion = s.get("ampliacion", False)
    seguro = s.get("seguro", False)

    # recargo comuna
    if "hospicio" in comuna:
        base += 40000

    # escala base
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

    # baños adicionales
    if banos > 1:
        factor += (banos - 1) * 0.1

    # ampliaciones
    if ampliacion:
        factor += 0.2

    precio_servicio = int(base * factor)
    total = precio_servicio + (60000 if seguro else 0)

    # guardar en sesión para posible aceptación posterior
    s["precio_servicio"] = precio_servicio
    s["total"] = total

    # correo de cotización
    enviar_correo_cotizacion(s, precio_servicio, total)

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
        "✔ Incluye localización precisa de la filtración\n"
        "✔ Equipos especializados para detección\n"
        "✔ Minimiza demoliciones innecesarias\n\n"
        f"Nombre: {s['nombre']}\n"
        f"Teléfono: {s['telefono']}\n\n"
        "Indícanos si estás de acuerdo para generar la *cotización oficial* con los alcances del servicio, condiciones de pago, garantías y agendar el inicio del servicio.\n"
        "Contamos con todos los medios de pago disponibles."
    )

    return respuesta


# =========================
# LÓGICA PRINCIPAL
# =========================

def handle_message(user, text):
    if user not in sessions:
        sessions[user] = {"step": "menu"}

    session = sessions[user]

    # Reinicio manual
    if text in ["menu", "menú", "inicio", "hola", "reiniciar"]:
        sessions[user] = {"step": "menu"}
        return menu()

    # aceptación de propuesta
    if session.get("step") == "fin" and es_aceptacion(text):
        enviar_correo_aceptacion(session)
        return (
            "Excelente 👍\n\n"
            "Hemos registrado tu aceptación del valor estimado.\n"
            "A continuación generaremos la *cotización oficial* con los alcances del servicio, condiciones de pago, garantías y coordinación de agenda.\n\n"
            "Un ejecutivo te contactará a la brevedad."
        )

    # ================= MENU =================
    if session["step"] == "menu":
        servicio_detectado = detectar_servicio(text)

        if servicio_detectado == "filtracion":
            session["service"] = "filtracion"
            session["step"] = "tipo_propiedad"
            return (
                "Perfecto 👍\n\n"
                "Para estimar la localización de la filtración necesitamos algunos datos de la propiedad.\n\n"
                "Esto nos permite ajustar la complejidad del trabajo y evitar intervenciones innecesarias.\n\n"
                "¿Es *casa* o *departamento*?"
            )

        if servicio_detectado == "alcantarillado":
            session["service"] = "alcantarillado"
            session["step"] = "contacto_nombre"
            return (
                "Entiendo 👍 esto parece un problema de *alcantarillado u olores*.\n\n"
                "Indícame tu *nombre* para coordinar la evaluación técnica."
            )

        if servicio_detectado == "piscina":
            session["service"] = "piscina"
            session["step"] = "contacto_nombre"
            return (
                "Perfecto 👍 te ayudaremos con tu *piscina*.\n\n"
                "Indícame tu *nombre* y te contactaremos para revisar el caso."
            )

        if servicio_detectado == "seguro":
            session["service"] = "seguro"
            session["step"] = "contacto_nombre"
            return (
                "Claro 👍 realizamos *informes técnicos para seguros*.\n\n"
                "Indícame tu *nombre* para orientarte."
            )

        if servicio_detectado == "inspeccion":
            session["service"] = "inspeccion"
            session["step"] = "contacto_nombre"
            return (
                "Perfecto 👍 realizamos *inspecciones técnicas y auditorías*.\n\n"
                "Indícame tu *nombre* para coordinar la evaluación."
            )

        if text == "1":
            session["service"] = "filtracion"
            session["step"] = "tipo_propiedad"
            return (
                "Perfecto 👍\n\n"
                "Para estimar la localización de la filtración necesitamos algunos datos de la propiedad.\n\n"
                "Esto nos permite ajustar la complejidad del trabajo y evitar intervenciones innecesarias.\n\n"
                "¿Es *casa* o *departamento*?"
            )

        if text == "2":
            session["service"] = "alcantarillado"
            session["step"] = "contacto_nombre"
            return "Para alcantarillado u olores se requiere evaluación técnica.\n\nIndícame tu *nombre*."

        if text == "3":
            session["service"] = "piscina"
            session["step"] = "contacto_nombre"
            return "Para piscinas primero realizamos diagnóstico técnico.\n\nIndícame tu *nombre*."

        if text == "4":
            session["service"] = "inspeccion"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para coordinar la inspección técnica."

        if text == "5":
            session["service"] = "seguro"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para preparar el informe técnico."

        if text == "6":
            session["service"] = "auditoria"
            session["step"] = "contacto_nombre"
            return "Perfecto. Indícame tu *nombre* para coordinar la auditoría."

        if text == "7":
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
    print("Mensaje recibido:", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        user = msg["from"]
        text = msg.get("text", {}).get("body", "").strip().lower()

        # registrar interacción entrante
        current_session = sessions.get(user, {"step": "menu"})
        enviar_correo_interaccion(user, "CLIENTE → BOT", text, current_session)

        response = handle_message(user, text)
        if response:
            send_message(user, response)

    except Exception as e:
        print("Error en webhook:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
