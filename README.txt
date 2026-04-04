# FÉNIX Bot en Render

## Archivos
- `app.py`: bot Flask para WhatsApp
- `requirements.txt`: dependencias
- `render.yaml`: despliegue en Render

## Variables que debes completar en Render
- `VERIFY_TOKEN`: texto inventado por ti, por ejemplo `fenix123`
- `WHATSAPP_TOKEN`: token de WhatsApp Cloud API
- `PHONE_NUMBER_ID`: Phone Number ID del número nuevo
- `EMAIL_REMITENTE`: correo que enviará las alertas
- `EMAIL_PASSWORD_APP`: contraseña de aplicación del correo remitente
- `EMAIL_DESTINO`: ya viene configurado en `alfredo.jimenez@tengounafuga.cl`

## Pasos rápidos en Render
1. Sube estos archivos a GitHub en un repositorio nuevo.
2. En Render, crea un **New + > Blueprint** y conecta ese repositorio.
3. Completa las variables de entorno.
4. Espera el deploy.
5. Copia la URL pública de Render.
6. En Meta Developers > WhatsApp > Configuration:
   - Callback URL = `https://TU-URL.onrender.com/webhook`
   - Verify Token = el mismo `VERIFY_TOKEN`
7. Suscribe el campo `messages`.
8. Escribe "Hola" al número nuevo y prueba.

## Salud del servicio
- `https://TU-URL.onrender.com/health`