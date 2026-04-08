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
        print("Error:", e)

    return "ok", 200


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

    if session["step"] == "menu":
        if text == "1" or "filtr" in text or "fuga" in text:
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

    if session.get("service") == "filtracion":

        if session["step"] == "tipo_propiedad":
            if "casa" in text:
                session["tipo"] = "casa"
                session["step"] = "comuna"
                return "¿En qué *comuna* se encuentra? Responde: *Iquique* o *Alto Hospicio*."

            if "depart" in text or "depto" in text or "condominio" in text or "industria" in text:
                session["tipo"] = "departamento"
                session["step"] = "contacto_nombre"
                return "Para departamentos, condominios o industrias realizamos *visita técnica*.\n\nIndícame tu *nombre*."

            return "Por favor responde si es *casa* o *departamento*."

        if session["step"] == "comuna":
            session["comuna"] = text
            session["step"] = "m2"
            return "¿Cuántos *m² aproximados* tiene la propiedad? Responde solo con el número."

        if session["step"] == "m2":
            try:
                session["m2"] = int("".join(filter(str.isdigit, text)))
            except:
                return "Indica solo el número de *m²*."
            session["step"] = "banos"
            return "¿Cuántos *baños* tiene la propiedad? Responde solo con el número."

        if session["step"] == "banos":
            try:
                session["banos"] = int("".join(filter(str.isdigit, text)))
            except:
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
# MENÚ
# =========================

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


# =========================
# COTIZACIÓN
# =========================

def calcular_cotizacion(s):
    base = 270000

    comuna = s.get("comuna", "").lower()
    m2 = s.get("m2", 0)
    banos = s.get("banos", 1)
    ampliacion = s.get("ampliacion", False)
    seguro = s.get("seguro", False)

    # Base según comuna
    if "hospicio" in comuna:
        base += 40000

    # Factor base según superficie
    if m2 <= 100:
        factor = 1.0
        tramo = "Casa hasta 100 m²"
    elif m2 <= 200:
        factor = 1.5
        tramo = "Casa sobre 100 m² y hasta 200 m²"
    elif m2 <= 300:
        factor = 2.0
        tramo = "Casa sobre 200 m² y hasta 300 m²"
    else:
        factor = 2.5
        tramo = "Casa sobre 300 m²"

    detalle_factor = [f"Factor base: x{factor:.1f} ({tramo})"]

    # +0.1 por cada baño adicional
    if banos > 1:
        incremento_banos = (banos - 1) * 0.1
        factor += incremento_banos
        detalle_factor.append(f"+{incremento_banos:.1f} por {banos - 1} baño(s) adicional(es)")

    # +0.2 si hay ampliaciones
    if ampliacion:
        factor += 0.2
        detalle_factor.append("+0.2 por ampliaciones")

    precio = int(base * factor)

    # +60000 informe para seguro
    if seguro:
        precio += 60000
        detalle_factor.append("+60.000 por informe para seguro")

    detalle_texto = "\n".join(detalle_factor)

    return (
        "💧 *Cotización estimada*\n\n"
        f"💰 CLP {precio:,}".replace(",", ".") +
        "\n\nDetalle:\n"
        f"{detalle_texto}\n"
        f"Factor total aplicado: x{factor:.1f}\n"
        f"Superficie: {m2} m²\n"
        f"Baños: {banos}\n"
        f"Ampliaciones: {'Sí' if ampliacion else 'No'}\n"
        f"Comuna: {s['comuna'].title()}\n"
        f"Informe para seguro: {'Sí' if seguro else 'No'}\n\n"
        f"Nombre: {s['nombre']}\n"
        f"Teléfono: {s['telefono']}\n"
        f"Correo: {s['correo']}\n\n"
        "¿Deseas agendar visita?"
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

    response = requests.post(url, json=payload, headers=headers)
    print("Respuesta enviada:", response.text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
