from flask import Flask, request

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import requests


app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "fenix123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

sessions = {}

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

BASE_PRICE = 180000
PRECIO_DIESEL = 1300
VALOR_INFORME = 60000

LOCALIDADES = {
    "iquique": {"km": 0, "extra_fijo": 0},
    "alto hospicio": {"km": 0, "extra_fijo": 20000},
    "pozo almonte": {"km": 110, "extra_fijo": 0},
    "pica": {"km": 240, "extra_fijo": 0},
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
    if "iquique" in texto:
        return "iquique"

    return "iquique"


def es_aceptacion(texto):
    texto = texto.lower().strip()
    afirmativos = [
        "si", "sí", "ok", "acepto", "de acuerdo",
        "adelante", "avancemos", "confirmo", "agendar", "quiero"
    ]
    return any(x in texto for x in afirmativos)


def solicita_humano(texto):
    texto = texto.lower().strip()
    palabras = [
        "humano", "asesor", "especialista", "persona", "ejecutivo",
        "llamar", "llamen", "contactar", "quiero hablar"
    ]
    return any(p in texto for p in palabras)


def detectar_servicio(texto):
    texto = texto.lower()

    if any(x in texto for x in [
        "filtracion", "filtración", "fuga", "humedad", "goteo", "pierde agua"
    ]):
        return "filtracion"

    if any(x in texto for x in [
        "alcantarillado", "olor", "hedor", "desague", "desagüe"
    ]):
        return "alcantarillado"

    if any(x in texto for x in ["piscina", "agua verde", "agua turbia"]):
        return "piscina"

    if any(x in texto for x in ["seguro", "informe", "aseguradora"]):
        return "seguro"

    if any(x in texto for x in [
        "inspeccion", "inspección", "auditoria", "auditoría"
