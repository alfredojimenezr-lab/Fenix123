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

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

BASE_PRICE = 250000
PRECIO_DIESEL = 1300
VALOR_INFORME = 60000

LOCALIDADES = {
    "iquique": {
        "km": 0,
        "extra_fijo": 0
    },

    "alto hospicio": {
        "km": 0,
        "extra_fijo": 40000
    },

    "pozo almonte": {
        "km": 110,
        "extra_fijo": 0
    },

    "pica": {
        "km": 240,
        "extra_fijo": 0
    },

    "arica": {
        "km": 600,
        "extra_fijo": 0
    }
}


# =====================================================
# UTILIDADES
# =====================================================

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalizar_localidad(texto):

    texto = texto.lower().strip()

    if "alto" in texto or "hospicio" in texto:
        return "alto hospicio"

    if "pozo" in texto or "almonte" in texto:
        return "pozo almonte"

    if "pica" in texto:
        return "pica"

    if "arica" in texto:
        return "arica"

    if "iquique" in texto:
        return "iquique"

    return "iquique"


def es_aceptacion(texto):

    texto = texto.lower().strip()

    afirmativos = [
        "si",
        "sí",
        "ok",
        "acepto",
        "de acuerdo",
        "adelante",
        "avancemos",
        "confirmo",
        "agendar",
        "quiero"
    ]

    return any(x in texto for x in afirmativos)


def detectar_servicio(texto):

    texto = texto.lower()

    if any(x in texto for x in [
        "filtracion",
        "filtración",
        "fuga",
        "humedad",
        "goteo",
        "pierde agua"
    ]):
        return "filtracion"

    if any(x in texto for x in [
        "alcantarillado",
        "olor",
        "hedor",
        "desague",
        "desagüe"
    ]):
        return "alcantarillado"

    if any(x in texto for x in [
        "piscina",
        "agua verde",
        "agua turbia"
    ]):
        return "piscina"

    if any(x in texto for x in [
        "seguro",
        "informe",
        "aseguradora"
    ]):
        return "seguro"

    if any(x in texto for x in [
        "inspeccion",
        "inspección",
        "auditoria",
        "auditoría"
    ]):
        return "inspeccion"

    return None


def calcular_traslado(localidad):

    localidad = localidad.lower()

    if localidad not in LOCALIDADES:
        return 0

    km = LOCALIDADES[localidad]["km"]

    if km == 0:
        return LOCALIDADES[localidad]["extra_fijo"]

    litros = km / 8

    costo = litros * PRECIO_DIESEL

    costo = costo * 1.15

    return int(costo)


# =====================================================
# CORREO
# =====================================================

def enviar_correo(asunto, cuerpo):

    try:

        remitente = os.environ.get("EMAIL_REMITENTE")
        clave = os.environ.get("EMAIL_PASSWORD_APP")
        destino = os.environ.get("EMAIL_DESTINO")

        msg = MIMEText(cuerpo, "plain", "utf-8")

        msg["Subject"] = asunto
        msg["From"] = remitente
        msg["To"] = destino

        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

        server.login(remitente, clave)

        server.send_message(msg)

        server.quit()

        print("Correo enviado")

    except Exception as e:

        print("Error correo:", e)


# =====================================================
# WHATSAPP
# =====================================================

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
        "text": {
            "body": text
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print(response.text)


# =====================================================
# MENÚ
# =====================================================

def menu():

    return (
        "Hola 👋 Soy *FÉNIX – Especialistas en detección de fugas*\n\n"

        "💧 Detectamos filtraciones sin romper de más\n"
        "📍 Atención en Iquique, Alto Hospicio, "
        "Pozo Almonte, Pica y Arica\n\n"

        "Selecciona una opción:\n\n"

        "1️⃣ Filtración de agua potable\n"
        "2️⃣ Olor / alcantarillado\n"
        "3️⃣ Problemas en piscina\n"
        "4️⃣ Inspección técnica\n"
        "5️⃣ Informe para seguro\n"
        "6️⃣ Auditoría técnica\n"
        "7️⃣ Otro\n\n"

        "Responde con el número o describe tu problema."
    )


# =====================================================
# COTIZACIÓN FILTRACIÓN CASA
# =====================================================

def calcular_cotizacion(s):

    localidad = s.get("localidad", "").lower()
    m2 = s.get("m2", 0)
    banos = s.get("banos", 1)
    ampliacion = s.get("ampliacion", False)
    seguro = s.get("seguro", False)

    # ==========================================
    # FACTOR COMPLEJIDAD
    # ==========================================

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

        s["step"] = "agenda_visita_dia"

        cuerpo = f"""
Nuevo requerimiento - Casa sobre 350 m2

Fecha: {ahora()}

Servicio: Filtración de agua potable

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Localidad: {localidad}
m2: {m2}
Baños: {banos}

Ampliación: {"Sí" if ampliacion else "No"}
Informe seguro: {"Sí" if seguro else "No"}

Requiere visita técnica sin costo.
"""

        enviar_correo(
            "Lead casa sobre 350 m2",
            cuerpo
        )

        return (
            "🏠 *Evaluación técnica en terreno*\n\n"

            "Para propiedades sobre 350 m² "
            "se requiere visita técnica sin costo.\n\n"

            "Indícanos por favor el *día* "
            "que te acomoda."
        )

    # ==========================================
    # AJUSTES
    # ==========================================

    if banos > 1:
        factor += (banos - 1) * 0.1

    if ampliacion:
        factor += 0.4

    precio_servicio = int(BASE_PRICE * factor)

    traslado = calcular_traslado(localidad)

    total = precio_servicio + traslado

    if seguro:
        total += VALOR_INFORME

    # guardar sesión
    s["precio_servicio"] = precio_servicio
    s["traslado"] = traslado
    s["total"] = total

    s["step"] = "fin"

    # ==========================================
    # CORREO
    # ==========================================

    cuerpo = f"""
Nueva cotización registrada

Fecha: {ahora()}

Nombre: {s.get('nombre')}
Teléfono: {s.get('telefono')}
Correo: {s.get('correo')}

Servicio: Filtración de agua potable

Localidad: {localidad}
m2: {m2}
Baños: {banos}

Ampliación: {"Sí" if ampliacion else "No"}
Informe seguro: {"Sí" if seguro else "No"}

Valor servicio: {precio_servicio}
Traslado: {traslado}
Total: {total}
"""

    enviar_correo(
        "Nueva cotización - Fenix Bot",
        cuerpo
    )

    # ==========================================
    # RESPUESTA
    # ==========================================

    respuesta = (
        "💧 *Precio estimado*\n\n"

        f"🔧 Localización y reparación: "
        f"CLP {precio_servicio:,}\n"
    ).replace(",", ".")

    if traslado > 0:

        respuesta += (
            f"🚚 Traslado ({localidad.title()}): "
            f"CLP {traslado:,}\n"
        ).replace(",", ".")

    if seguro:

        respuesta += (
            f"📄 Informe para seguro: "
            f"CLP {VALOR_INFORME:,}\n"
        ).replace(",", ".")

    respuesta += (
        f"\n💰 *Total estimado:* "
        f"CLP {total:,}\n\n"
    ).replace(",", ".")

    respuesta += (
        "✔ Incluye localización de la filtración y reparación\n"
        "✔ Equipos especializados\n"
        "✔ Minimiza demoliciones innecesarias\n\n"

        f"Nombre: {s['nombre']}\n"
        f"Teléfono: {s['telefono']}\n\n"

        "Indícanos si deseas avanzar "
        "para agendar el servicio."
    )

    return respuesta


# =====================================================
# LÓGICA PRINCIPAL
# =====================================================

def handle_message(user, text):

    if user not in sessions:
        sessions[user] = {
            "step": "menu"
        }

    session = sessions[user]

    text = text.lower().strip()

    # ==========================================
    # RESET
    # ==========================================

    if text in [
        "hola",
        "inicio",
        "menu",
        "menú"
    ]:

        sessions[user] = {
            "step": "menu"
        }

        return menu()

    # ==========================================
    # AGENDA CASA
    # ==========================================

    if session.get("step") == "agenda_casa_dia":

        session["dia_agenda"] = text

        cuerpo = f"""
Nueva agenda registrada

Fecha: {ahora()}

Servicio: Filtración casa

Nombre: {session.get('nombre')}
Teléfono: {session.get('telefono')}
Correo: {session.get('correo')}

Localidad: {session.get('localidad')}

Día agenda: {text}

Precio servicio: {session.get('precio_servicio')}
Traslado: {session.get('traslado')}
Total: {session.get('total')}
"""

        enviar_correo(
            "Nueva agenda casa",
            cuerpo
        )

        session["step"] = "cerrado"

        return (
            f"📅 Agenda registrada para el día: "
            f"*{text}*\n\n"

            "Un ejecutivo te contactará "
            "para confirmar."
        )

    # ==========================================
    # AGENDA VISITA TÉCNICA
    # ==========================================

    if session.get("step") == "agenda_visita_dia":

        session["dia_agenda"] = text

        session["step"] = "agenda_visita_bloque"

        return (
            "Perfecto 👍\n\n"

            "Indícanos el bloque horario:\n\n"

            "🌞 Mañana\n"
            "🌙 Tarde"
        )

    if session.get("step") == "agenda_visita_bloque":

        if "mañ" in text:
            bloque = "Mañana"

        elif "tard" in text:
            bloque = "Tarde"

        else:
            return "Responde *mañana* o *tarde*."

        session["bloque_agenda"] = bloque

        cuerpo = f"""
Nueva visita técnica registrada

Fecha: {ahora()}

Servicio: {session.get('service')}

Nombre: {session.get('nombre')}
Teléfono: {session.get('telefono')}
Correo: {session.get('correo')}

Detalle:
{session.get('detalle')}

Día: {session.get('dia_agenda')}
Bloque: {bloque}
"""

        enviar_correo(
            "Nueva visita técnica",
            cuerpo
        )

        session["step"] = "cerrado"

        return (
            "📅 Agenda registrada\n\n"

            f"Día: {session.get('dia_agenda')}\n"
            f"Bloque: {bloque}\n\n"

            "Un ejecutivo te contactará "
            "para confirmar."
        )

    # ==========================================
    # ACEPTACIÓN COTIZACIÓN
    # ==========================================

    if (
        session.get("step") == "fin"
        and session.get("service") == "filtracion"
        and es_aceptacion(text)
    ):

        cuerpo = f"""
Cliente aceptó cotización

Fecha: {ahora()}

Nombre: {session.get('nombre')}
Teléfono: {session.get('telefono')}
Correo: {session.get('correo')}

Localidad: {session.get('localidad')}

Total: {session.get('total')}
"""

        enviar_correo(
            "Cliente aceptó cotización",
            cuerpo
        )

        session["step"] = "agenda_casa_dia"

        return (
            "Excelente 👍\n\n"

            "Tu aceptación fue registrada.\n\n"

            "Indícanos el *día* "
            "que te acomoda."
        )

    # ==========================================
    # CERRADO
    # ==========================================

    if session.get("step") == "cerrado":

        return (
            "Tu solicitud ya fue registrada.\n\n"

            "Si deseas comenzar nuevamente "
            "escribe *inicio*."
        )

    # ==========================================
    # MENÚ
    # ==========================================

    if session["step"] == "menu":

        servicio = detectar_servicio(text)

        if text == "1" or servicio == "filtracion":

            session["service"] = "filtracion"
            session["step"] = "tipo"

            return (
                "Perfecto 👍\n\n"

                "¿La propiedad corresponde a:\n\n"

                "🏠 Casa\n"
                "🏢 Departamento / Condominio?"
            )

        if text == "2" or servicio == "alcantarillado":

            session["service"] = "alcantarillado"
            session["step"] = "detalle"

            return (
                "Describe brevemente el problema "
                "de alcantarillado u olores."
            )

        if text == "3" or servicio == "piscina":

            session["service"] = "piscina"
            session["step"] = "detalle"

            return (
                "Describe brevemente "
                "el problema de la piscina."
            )

        if text == "4" or servicio == "inspeccion":

            session["service"] = "inspeccion"
            session["step"] = "detalle"

            return (
                "Describe brevemente "
                "la inspección requerida."
            )

        if text == "5" or servicio == "seguro":

            session["service"] = "seguro"
            session["step"] = "detalle"

            return (
                "Describe brevemente "
                "lo que necesitas."
            )

        if text == "6":

            session["service"] = "auditoria"
            session["step"] = "detalle"

            return (
                "Describe brevemente "
                "la auditoría requerida."
            )

        if text == "7":

            session["service"] = "otro"
            session["step"] = "detalle"

            return (
                "Cuéntanos brevemente "
                "qué necesitas."
            )

        return menu()

    # ==========================================
    # FILTRACIÓN
    # ==========================================

    if session.get("service") == "filtracion":

        if session["step"] == "tipo":

            if "casa" in text:

                session["tipo"] = "casa"
                session["step"] = "localidad"

                return (
                    "Indica la localidad:\n\n"

                    "📍 Iquique\n"
                    "📍 Alto Hospicio\n"
                    "📍 Pozo Almonte\n"
                    "📍 Pica\n"
                    "📍 Arica"
                )

            if (
                "depart" in text
                or "depto" in text
                or "condominio" in text
                or "industria" in text
            ):

                session["tipo"] = "visita"
                session["step"] = "contacto_nombre"

                return (
                    "🏢 Para departamentos, "
                    "condominios e industrias "
                    "realizamos visita técnica "
                    "sin costo.\n\n"

                    "Indícanos tu nombre."
                )

            return "Responde casa o departamento."

        if session["step"] == "localidad":

            session["localidad"] = normalizar_localidad(text)

            session["step"] = "m2"

            return (
                "¿Cuántos m² aproximados "
                "tiene la propiedad?"
            )

        if session["step"] == "m2":

            try:

                session["m2"] = int(
                    "".join(filter(str.isdigit, text))
                )

            except:

                return "Indica solo el número."

            session["step"] = "banos"

            return "¿Cuántos baños tiene?"

        if session["step"] == "banos":

            try:

                session["banos"] = int(
                    "".join(filter(str.isdigit, text))
                )

            except:

                return "Indica solo el número."

            session["step"] = "ampliacion"

            return (
                "¿La propiedad tiene ampliaciones?\n\n"

                "Responde sí o no."
            )

        if session["step"] == "ampliacion":

            session["ampliacion"] = (
                text in ["si", "sí", "s"]
            )

            session["step"] = "seguro"

            return (
                "¿Requiere informe para seguro?\n\n"

                "Responde sí o no."
            )

        if session["step"] == "seguro":

            session["seguro"] = (
                text in ["si", "sí", "s"]
            )

            session["step"] = "nombre"

            return "Indícanos tu nombre."

        if session["step"] == "nombre":

            session["nombre"] = text.title()

            session["step"] = "telefono"

            return "Indícanos tu teléfono."

        if session["step"] == "telefono":

            session["telefono"] = text

            session["step"] = "correo"

            return "Indícanos tu correo electrónico."

        if session["step"] == "correo":

            session["correo"] = text

            return calcular_cotizacion(session)

    # ==========================================
    # OTROS SERVICIOS
    # ==========================================

    if session["step"] == "detalle":

        session["detalle"] = text

        session["step"] = "contacto_nombre"

        return "Indícanos tu nombre."

    if session["step"] == "contacto_nombre":

        session["nombre"] = text.title()

        session["step"] = "contacto_telefono"

        return "Indícanos tu teléfono."

    if session["step"] == "contacto_telefono":

        session["telefono"] = text

        session["step"] = "contacto_correo"

        return "Indícanos tu correo electrónico."

    if session["step"] == "contacto_correo":

        session["correo"] = text

        cuerpo = f"""
Nuevo requerimiento registrado

Fecha: {ahora()}

Servicio: {session.get('service')}

Nombre: {session.get('nombre')}
Teléfono: {session.get('telefono')}
Correo: {session.get('correo')}

Detalle:
{session.get('detalle')}
"""

        enviar_correo(
            "Nuevo requerimiento",
            cuerpo
        )

        session["step"] = "agenda_visita_dia"

        return (
            "Perfecto 👍\n\n"

            "Indícanos el *día* "
            "que te acomoda para coordinar "
            "la visita."
        )

    return menu()


# =====================================================
# WEBHOOK
# =====================================================

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

        message = value["messages"][0]

        from_number = message["from"]

        incoming = (
            message.get("text", {})
            .get("body", "")
            .lower()
            .strip()
        )

        response = handle_message(
            from_number,
            incoming
        )

        if response:
            send_message(from_number, response)

    except Exception as e:

        print("Error:", e)

    return "ok", 200


@app.route("/")
def home():

    return "Bot activo", 200


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
