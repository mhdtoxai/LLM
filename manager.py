import os
import requests
import json
from dotenv import load_dotenv
from prompts import PROMPT_CLASIFICADOR, PROMPT_CONSULTAS, PROMPT_ACCIONES

load_dotenv()

SAPTIVA_API_KEY = os.getenv("SAPTIVA_API_KEY")
SAPTIVA_URL = "https://api.saptiva.com/v1/chat/completions"

# Usa sesión para reducir overhead de conexión
session = requests.Session()

# --- UTILIDAD: Extraer JSON válido ---

def extraer_json_valido(texto: str) -> dict:
    try:
        texto_limpio = texto.strip().replace("```json", "").replace("```", "")
        return json.loads(texto_limpio)
    except Exception as e:
        print(f"⚠️ Error parseando intención: {e} | Respuesta cruda: {texto}")
        return {}

# --- DETECTOR DE INTENCIÓN ---

def detectar_intencion(message: str) -> str:
    try:
        response = session.post(
            SAPTIVA_URL,
            headers={
                "Authorization": f"Bearer {SAPTIVA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "Saptiva Turbo",
                "messages": [
                    {"role": "system", "content": PROMPT_CLASIFICADOR},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.0,
                "max_tokens": 50
            },
            timeout=15
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        data = extraer_json_valido(raw)
        return data.get("intencion", "consulta_general")
    except Exception as e:
        print(f"❌ Error en clasificador: {e}")
        return "consulta_general"

# --- MANAGER PRINCIPAL ---

def ai_manager(message: str, member: bool = False) -> str:
    print(f"📩 Mensaje: '{message}' | ¿Miembro?: {member}")

    intencion = detectar_intencion(message)
    print(f"🔍 Intención detectada: {intencion}")

    if intencion == "fuera_de_dominio":
        return "Lo siento, solo puedo ayudarte con información relacionada con CANACO SERVYTUR León."

    # Siempre usamos Saptiva Turbo
    modelo = "Saptiva Turbo"

    if intencion == "consulta_general":
        prompt = PROMPT_CONSULTAS
    elif intencion == "accion_personal":
        if not member:
            return "Esta información está disponible solo para miembros afiliados a CANACO SERVYTUR León. Si deseas afiliarte, con gusto te explico cómo hacerlo. 😊"
        prompt = PROMPT_ACCIONES
    else:
        # Fallback seguro
        prompt = PROMPT_CONSULTAS

    try:
        response = session.post(
            SAPTIVA_URL,
            headers={
                "Authorization": f"Bearer {SAPTIVA_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.2,
                "max_tokens": 400
            },
            timeout=20
        )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return "No se pudo generar una respuesta. Intenta de nuevo."
        return content.strip().replace("<think>", "").replace("</think>", "")
    except Exception as e:
        print(f"❌ Error al consultar Saptiva: {e}")
        return "Ocurrió un error al generar la respuesta."
