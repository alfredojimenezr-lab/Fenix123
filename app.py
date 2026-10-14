if session["step"] == "m2":
            try:
                session["m2"] = int("".join(filter(str.isdigit, text)))
            except (TypeError, ValueError):
                return "Indica solo el número."
            session["step"] = "banos"
            return "¿Cuántos baños tiene?"

        if session["step"] == "banos":
            try:
                session["banos"] = int("".join(filter(str.isdigit, text)))
            except (TypeError, ValueError):
                return "Indica solo el número."
            session["step"] = "ampliacion"
            return "¿La propiedad tiene ampliaciones?\n\nResponde sí o no."

        if session["step"] == "ampliacion":
            session["ampliacion"] = text in ["si", "sí", "s"]
            session["step"] = "seguro"
            return "¿Requiere informe para seguro?\n\nResponde sí o no."

        if session["step"] == "seguro":
            session["seguro"] = text in ["si", "sí", "s"]
            session["step"] = "nombre"
            return "Indícanos tu nombre."

        if session["step"] == "nombre":
            session["nombre"] = raw_text.title()
            session["step"] = "telefono"
            return "Indícanos tu teléfono."

        if session["step"] == "telefono":
            session["telefono"] = raw_text
            session["step"] = "correo"
            return "Indícanos tu correo electrónico."

        if session["step"] == "correo":
            session["correo"] = raw_text
            session["step"] = "direccion_casa"
            return (
                "Para completar tu solicitud, indícanos la *dirección del inmueble*: "
                "calle y número y, si corresponde, departamento, torre o casa."
            )

    # OTROS SERVICIOS
    if session.get("step") == "detalle":
        session["detalle"] = raw_text
        session["step"] = "contacto_nombre"
        return "Indícanos tu nombre."

    if session.get("step") == "contacto_nombre":
        session["nombre"] = raw_text.title()
        session["step"] = "contacto_telefono"
        return "Indícanos tu teléfono."

    if session.get("step") == "contacto_telefono":
        session["telefono"] = raw_text
        session["step"] = "contacto_correo"
        return "Indícanos tu correo electrónico."

    if session.get("step") == "contacto_correo":
        session["correo"] = raw_text
        session["step"] = "contacto_direccion"
        return (
            "Para completar tu solicitud, indícanos la *dirección del inmueble*: "
            "calle y número y, si corresponde, departamento, torre o casa y comuna."
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
        incoming = message.get("text", {}).get("body", "").strip()
        response = handle_message(from_number, incoming)
        if response:
            send_message(from_number, response)

    except Exception as e:
        print("Error:", e)

    return "ok", 200


@app.route("/")
def home():
    return "Bot activo", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
