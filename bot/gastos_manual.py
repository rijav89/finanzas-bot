"""
gastos_manual.py — FinanzasBot v3.1
Detecta intención y extrae datos con Qwen (OpenAI-compatible API).
"""

import json
from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_TEXT
from categorias import catalogo

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)


def _opciones(tipo: str, usuario_id=None) -> list:
    """El catálogo se lee de la base (incluye las categorías propias del usuario):
    armarlo a mano acá lo desincronizaría de lo que el panel ofrece."""
    return list(catalogo(tipo, usuario_id))


def _validar(valor, opciones: list, defecto: str) -> str:
    """El modelo a veces responde con tildes o mayúsculas distintas."""
    if isinstance(valor, str):
        for c in opciones:
            if c.lower() == valor.strip().lower():
                return c
    return defecto


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
  "categoria": "<{categorias}>",
  "medio": "<Yape|Plin|Transferencia|Efectivo|Depósito|No especificado>",
  "cuenta_destino": "<nombre de cuenta o Principal>",
  "fecha": "<YYYY-MM-DD>"
}}"""

def extraer_ingreso(mensaje: str, cuentas=None, usuario_id=None) -> dict:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    opciones = _opciones("ingreso", usuario_id)
    try:
        raw = _call(PROMPT_INGRESO.format(
            mensaje=mensaje, hoy=hoy, cuentas=cuentas_str, categorias="|".join(opciones),
        ))
        datos = json.loads(raw)
        datos["categoria"] = _validar(datos.get("categoria"), opciones, "Otros ingresos")
        return datos
    except Exception:
        return {"monto": 0, "descripcion": "Ingreso desconocido", "categoria": "Otros ingresos", "medio": "No especificado", "cuenta_destino": "Principal", "fecha": hoy}


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
      "categoria": "<{categorias}>",
      "cuenta_origen": "<nombre de cuenta o Principal>"
    }}
  ]
}}
Adapta 'fecha' según mencione el usuario (ej. "ayer" resta 1 día). Si no menciona, usa {hoy}."""

def extraer_gastos(mensaje: str, cuentas=None, usuario_id=None) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    opciones = _opciones("gasto", usuario_id)
    try:
        raw = _call(PROMPT_GASTOS.format(
            mensaje=mensaje, hoy=hoy, cuentas=cuentas_str, categorias="|".join(opciones),
        ))
        data = json.loads(raw)
        gastos = data.get("gastos", [])
        for g in gastos:
            g["categoria"] = _validar(g.get("categoria"), opciones, "Otros")
        return gastos, data.get("fecha", hoy)
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
  "categoria": "<{categorias} o vacío>"
}}"""

def extraer_edicion(mensaje: str, usuario_id=None) -> dict:
    try:
        raw = _call(PROMPT_EDICION.format(
            mensaje=mensaje, categorias="|".join(_opciones("gasto", usuario_id)),
        ))
        return json.loads(raw)
    except Exception:
        return {"monto": 0, "descripcion": "", "categoria": ""}
