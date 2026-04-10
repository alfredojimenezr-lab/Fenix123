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

Servicio solicitado: Filtración de agua potable
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

Servicio solicitado: Filtración de agua potable
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


def enviar_correo_lead_general(s):
    service = s.get("service", "No informado")

    nombres_servicio = {
        "alcantarillado": "Alcantarillado / olores",
        "piscina": "Piscina",
        "seguro": "Informe para seguro",
        "inspeccion": "Inspección técnica",
        "auditoria": "Auditoría técnica",
        "otro": "Otro",
        "filtracion": "Filtración"
    }

    servicio_nombre = nombres_servicio.get(service, service)
    detalle_adicional = s.get("detalle", "No informado")

    cuerpo = f"""
Nuevo requerimiento registrado

Fecha: {ahora()}

Servicio solicitado: {servicio_nombre}

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo', 'No informado')}

Detalle del requerimiento:
{detalle_adicional}
"""

    enviar_correo_generico(f"Nuevo requerimiento - {servicio_nombre}", cuerpo)


def enviar_correo_visita_tecnica_casa_grande(s):
    cuerpo = f"""
Nuevo requerimiento - Casa sobre 350 m2

Fecha: {ahora()}

Servicio solicitado: Filtración de agua potable
Tipo propiedad: {s.get('tipo')}
Condición: Casa sobre 350 m2 - requiere visita técnica sin costo

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Comuna: {s.get('comuna')}
Superficie: {s.get('m2')} m2
Baños: {s.get('banos')}
Ampliaciones: {"Sí" if s.get("ampliacion") else "No"}
Informe para seguro: {"Sí" if s.get("seguro") else "No"}
"""

    enviar_correo_generico("Lead nuevo - Casa sobre 350 m2", cuerpo)


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
# COTIZACIÓN FILTRACIÓN CASA
# =========================

def calcular_cotizacion(s):
    base = 300000

    comuna = s.get("comuna", "").lower()
    m2 = s.get("m2", 0)
    banos = s.get("banos", 1)
    ampliacion = s.get("ampliacion", False)
    seguro = s.get("seguro", False)

    if "hospicio" in comuna:
        base += 40000

    # Casa sobre 350 m2 -> visita técnica y correo
    if m2 > 350:
        enviar_correo_visita_tecnica_casa_grande(s)

        return (
            "🏠 *Evaluación técnica en terreno*\n\n"
            "Para casas de *más de 350 m²* realizamos una *visita técnica sin costo*, "
            "ya que la magnitud de la propiedad requiere evaluar en terreno las condiciones de localización y reparación.\n\n"
            "Luego de la visita generamos la *cotización oficial* con los alcances del servicio, condiciones de pago y garantías.\n\n"
            f"Nombre: {s['nombre']}\n"
            f"Teléfono: {s['telefono']}\n\n"
            "Indícanos si deseas avanzar para coordinar la visita técnica."
        )

    # Escala base
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
    else:  # <= 350
        factor = 3.5

    # Baños adicionales
    if banos > 1:
        factor += (banos - 1) * 0.1

    # Ampliaciones
    if ampliacion:
        factor += 0.4

    precio_servicio = int(base * factor)
    total = precio_servicio + (60000 if seguro else 0)

    s["precio_servicio"] = precio_servicio
    s["total"] = total

    enviar_correo_cotizacion(s, precio_servicio, total)

    respuesta = (
        "💧 *Precio estimado*\n\n"
        f"💰 Localización de la filtración y reparación: CLP {precio_servicio:,}".replace(",", ".") +
        "\n"
    )

    if seguro:
        respuesta += "📄 Informe para seguro: CLP 60.000\n"
        respuesta += f"\n💵 Total estimado: CLP {total:,}".replace(",", ".")

    respuesta += (
        "\n\n"
        "✔ Incluye localización de la filtración y reparación\n"
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

    if text in ["menu", "menú", "inicio", "hola", "reiniciar"]:
        sessions[user] = {"step": "menu"}
        return menu()

    if session.get("step") == "fin" and session.get("service") == "filtracion" and session.get("tipo") == "casa" and es_aceptacion(text):
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
            session["step"] = "detalle"
            return (
                "Entiendo 👍 esto parece un problema de *alcantarillado u olores*.\n\n"
                "Descríbenos brevemente el problema para registrarlo."
            )

        if servicio_detectado == "piscina":
            session["service"] = "piscina"
            session["step"] = "detalle"
            return (
                "Perfecto 👍 te ayudaremos con tu *piscina*.\n\n"
                "Descríbenos brevemente el problema para registrarlo."
            )

        if servicio_detectado == "seguro":
            session["service"] = "seguro"
            session["step"] = "detalle"
            return (
                "Claro 👍 realizamos *informes técnicos para seguros*.\n\n"
                "Descríbenos brevemente lo que necesitas para registrarlo."
            )

        if servicio_detectado == "inspeccion":
            session["service"] = "inspeccion"
            session["step"] = "detalle"
            return (
                "Perfecto 👍 realizamos *inspecciones técnicas y auditorías*.\n\n"
                "Descríbenos brevemente el objetivo de la evaluación."
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
            session["step"] = "detalle"
            return "Perfecto. Describe brevemente el problema de alcantarillado u olores."

        if text == "3":
            session["service"] = "piscina"
            session["step"] = "detalle"
            return "Perfecto. Describe brevemente el problema de la piscina."

        if text == "4":
            session["service"] = "inspeccion"
            session["step"] = "detalle"
            return "Perfecto. Describe brevemente el objetivo de la inspección técnica."

        if text == "5":
            session["service"] = "seguro"
            session["step"] = "detalle"
            return "Perfecto. Describe brevemente lo que necesitas para el informe técnico."

        if text == "6":
            session["service"] = "auditoria"
            session["step"] = "detalle"
            return "Perfecto. Describe brevemente el objetivo de la auditoría."

        if text == "7":
            session["service"] = "otro"
            session["step"] = "detalle"
            return "Cuéntanos brevemente qué necesitas."

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
                session["detalle"] = "Filtración en departamento, condominio o industria"
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

    # ================= RESTO DE SERVICIOS =================
    if session["step"] == "detalle":
        session["detalle"] = text
        session["step"] = "contacto_nombre"
        return "Perfecto. Indícame tu *nombre*."

    if session["step"] == "contacto_nombre":
        session["nombre"] = text.title()
        session["step"] = "contacto_telefono"
        return "Indícame tu *teléfono*."

    if session["step"] == "contacto_telefono":
        session["telefono"] = text
        session["step"] = "contacto_correo"
        return "Indícame tu *correo electrónico* o escribe *no* si no deseas informarlo."

    if session["step"] == "contacto_correo":
        session["correo"] = "" if text in ["no", "n"] else text
        session["step"] = "fin"

        if not (session.get("service") == "filtracion" and session.get("tipo") == "casa"):
            enviar_correo_lead_general(session)

        return (
            "Gracias 👍\n\n"
            f"Nombre: {session.get('nombre')}\n"
            f"Teléfono: {session.get('telefono')}\n\n"
            "Tu solicitud fue registrada correctamente. Un ejecutivo te contactará para coordinar la atención."
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

        response = handle_message(user, text)
        if response:
            send_message(user, response)

    except Exception as e:
        print("Error en webhook:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
