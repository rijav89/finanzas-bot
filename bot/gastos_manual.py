"""
gastos_manual.py — FinanzasBot v3.1
Detecta intención y extrae datos con Qwen (OpenAI-compatible API).
"""

import json
from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_TEXT

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

def _call(prompt: str) -> str:
    """Llamada base al modelo de texto."""
    response = client.chat.completions.create(
        model=QWEN_MODEL_TEXT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    raw = response.choices[0].message.content.strip()
    return raw.replace("```json", "").replace("```", "").strip()


# --- 1. Intención ---
INTENCIONES_VALIDAS = [
    "REGISTRAR_GASTOS", "INICIAR_REGISTRO", "REGISTRAR_INGRESO",
    "TRANSFERIR", "VER_RESUMEN", "VER_CATEGORIAS", "VER_HISTORIAL",
    "VER_SALDO", "EXPORTAR", "AYUDA", "FUERA_DE_TEMA",
]

PROMPT_INTENCION = """Eres un asistente de finanzas personales para usuarios en Perú llamado FinanzasBot.
El usuario escribió: "{mensaje}"
Clasifica la intención. Responde SOLO con un JSON válido:
{{"intencion": "<una de: {intenciones}>"}}
IMPORTANTE: Si el mensaje es saludo o charla genérica no relacionada a finanzas, usa "FUERA_DE_TEMA"."""

def detectar_intencion(mensaje: str) -> str:
    prompt = PROMPT_INTENCION.format(
        mensaje=mensaje,
        intenciones=", ".join(INTENCIONES_VALIDAS)
    )
    try:
        raw = _call(prompt)
        data = json.loads(raw)
        intencion = data.get("intencion", "FUERA_DE_TEMA")
        return intencion if intencion in INTENCIONES_VALIDAS else "FUERA_DE_TEMA"
    except Exception:
        return "FUERA_DE_TEMA"


# --- 2. Ingreso ---
PROMPT_INGRESO = """Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae los datos del ingreso. Responde SOLO con JSON válido:
{{
  "monto": <float>,
  "descripcion": "<descripción>",
  "medio": "<Yape|Plin|Transferencia|Efectivo|Depósito|No especificado>",
  "cuenta_destino": "<nombre de cuenta o Principal>",
  "fecha": "<YYYY-MM-DD>"
}}"""

def extraer_ingreso(mensaje: str, cuentas=None) -> dict:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    try:
        raw = _call(PROMPT_INGRESO.format(mensaje=mensaje, hoy=hoy, cuentas=cuentas_str))
        return json.loads(raw)
    except Exception:
        return {"monto": 0, "descripcion": "Ingreso desconocido", "medio": "No especificado", "cuenta_destino": "Principal", "fecha": hoy}


# --- 3. Gastos ---
PROMPT_GASTOS = """Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae fecha y lista de gastos. Responde SOLO con JSON válido:
{{
  "fecha": "<YYYY-MM-DD>",
  "gastos": [
    {{
      "monto": <float>,
      "descripcion": "<descripción>",
      "categoria": "<Comida|Supermercado|Transporte|Servicios|Salud|Educacion|Ropa|Entretenimiento|Tecnologia|Finanzas|Mascotas|Belleza|Hogar|Otros>",
      "cuenta_origen": "<nombre de cuenta o Principal>"
    }}
  ]
}}
Adapta 'fecha' según mencione el usuario (ej. "ayer" resta 1 día). Si no menciona, usa {hoy}."""

def extraer_gastos(mensaje: str, cuentas=None) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    try:
        raw = _call(PROMPT_GASTOS.format(mensaje=mensaje, hoy=hoy, cuentas=cuentas_str))
        data = json.loads(raw)
        return data.get("gastos", []), data.get("fecha", hoy)
    except Exception:
        return [], hoy


# --- 3.5 Transferencia ---
PROMPT_TRANSFERENCIA = """Cuentas disponibles: {cuentas}
Usuario quiere hacer una transferencia: "{mensaje}"
Responde SOLO con JSON válido:
{{
  "monto": <float>,
  "cuenta_origen": "<nombre de cuenta o Principal>",
  "cuenta_destino": "<nombre de cuenta>"
}}"""

def extraer_transferencia(mensaje: str, cuentas=None) -> dict:
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    try:
        raw = _call(PROMPT_TRANSFERENCIA.format(mensaje=mensaje, cuentas=cuentas_str))
        return json.loads(raw)
    except Exception:
        return {"monto": 0, "cuenta_origen": "", "cuenta_destino": ""}


# --- 4. Edición ---
PROMPT_EDICION = """Usuario quiere editar un gasto: "{mensaje}"
Responde SOLO con JSON válido:
{{
  "monto": <float o 0 si no se menciona>,
  "descripcion": "<nueva descripción o vacío>",
  "categoria": "<Comida|Supermercado|Transporte|Servicios|Salud|Educacion|Ropa|Entretenimiento|Tecnologia|Finanzas|Mascotas|Belleza|Hogar|Otros o vacío>"
}}"""

def extraer_edicion(mensaje: str) -> dict:
    try:
        raw = _call(PROMPT_EDICION.format(mensaje=mensaje))
        return json.loads(raw)
    except Exception:
        return {"monto": 0, "descripcion": "", "categoria": ""}
