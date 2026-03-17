"""
gastos_manual.py — FinanzasBot v2.8
Detecta la intención del mensaje del usuario.
"""

import json
from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT_INTENCION = """
Eres un asistente de finanzas personales para usuarios en Perú llamado FinanzasBot.

El usuario escribió: "{mensaje}"

Clasifica la intención en UNA de estas opciones:
- REGISTRAR_GASTOS: el usuario menciona uno o más gastos con montos explícitos (ej: "gasté 50 en almuerzo")
- INICIAR_REGISTRO: el usuario quiere registrar un gasto pero NO menciona montos ni detalles aún (ej: "quiero registrar un gasto", "registrar", "agregar gasto")
- REGISTRAR_INGRESO: el usuario menciona que recibió dinero, un pago, sueldo, ingreso, cobro, o quiere registrar un ingreso (ej: "me pagaron 4000", "cobré 500 de freelance", "recibí mi sueldo", "quiero registrar un ingreso")
- VER_RESUMEN: quiere ver el total gastado del mes (ej: "cuánto gasté", "resumen", "total")
- VER_CATEGORIAS: quiere ver el desglose por categoría (ej: "categorías", "estadísticas", "en qué gasté")
- VER_HISTORIAL: quiere ver sus últimas transacciones (ej: "historial", "mis gastos", "últimas transacciones")
- VER_SALDO: quiere ver su saldo o balance del mes (ej: "saldo", "balance", "cuánto me queda", "cuánto tengo")
- EXPORTAR: quiere descargar o exportar sus gastos (ej: "exportar", "excel", "descargar")
- AYUDA: quiere saber qué puede hacer el bot (ej: "ayuda", "qué puedes hacer", "cómo funciona")
- FUERA_DE_TEMA: cualquier otro mensaje no relacionado con finanzas personales

Responde ÚNICAMENTE con una de estas palabras exactas:
REGISTRAR_GASTOS, INICIAR_REGISTRO, REGISTRAR_INGRESO, VER_RESUMEN, VER_CATEGORIAS, VER_HISTORIAL, VER_SALDO, EXPORTAR, AYUDA, FUERA_DE_TEMA
"""

PROMPT_INGRESO = """
Eres un asistente de finanzas personales para usuarios en Perú.

El usuario escribió: "{mensaje}"

Extrae los datos del ingreso mencionado y responde ÚNICAMENTE con un JSON válido:
{{
  "monto": 4000.00,
  "descripcion": "sueldo",
  "medio": "Transferencia"
}}

Para "medio" usa uno de: Yape, Plin, Transferencia, Efectivo, Depósito, No especificado
Si no se menciona el medio, usa "No especificado".
Si no puedes determinar el monto, usa 0.
"""

PROMPT_GASTOS = """
Eres un asistente de finanzas personales para usuarios en Perú.
Hoy es {hoy}.

El usuario ha escrito el siguiente mensaje describiendo uno o varios gastos:
"{mensaje}"

Extrae TODOS los gastos mencionados y clasifica cada uno. También detecta si el usuario menciona una fecha distinta a hoy (ej: "ayer", "anteayer", "el lunes", "el martes pasado", "el 3 de marzo", "hace 2 días", etc.).

Responde ÚNICAMENTE con un JSON válido con esta estructura, sin texto adicional:
{{
  "fecha": "2025-03-10",
  "gastos": [
    {{
      "monto": 50.00,
      "descripcion": "menú",
      "categoria": "Comida"
    }}
  ]
}}

Categorías disponibles: Comida, Supermercado, Transporte, Servicios, Salud, Educacion, Ropa, Entretenimiento, Tecnologia, Finanzas, Mascotas, Belleza, Hogar, Otros

Reglas:
- "fecha" debe estar en formato YYYY-MM-DD
- Si no se menciona fecha específica, usa la fecha de hoy: {hoy}
- Si dice "ayer", resta 1 día a hoy. Si dice "anteayer", resta 2 días
- Si dice "el lunes", "el martes pasado", etc., calcula la fecha correcta hacia atrás desde hoy
- Si dice una fecha exacta como "el 3 de marzo", usa ese día con el año actual
- El monto debe ser un número decimal (sin S/)
- Si el usuario menciona "soles" o "sol", es la moneda peruana PEN
- La descripción debe ser corta y clara
- Si no puedes determinar el monto con certeza, omite ese gasto
- "gastos" debe ser lista vacía [] si no hay gastos válidos
"""


def detectar_intencion(mensaje: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_INTENCION.format(mensaje=mensaje)],
    )
    intencion = response.text.strip().upper()
    opciones_validas = {
        "REGISTRAR_GASTOS", "INICIAR_REGISTRO", "REGISTRAR_INGRESO",
        "VER_RESUMEN", "VER_CATEGORIAS", "VER_HISTORIAL", "VER_SALDO",
        "EXPORTAR", "AYUDA", "FUERA_DE_TEMA"
    }
    return intencion if intencion in opciones_validas else "FUERA_DE_TEMA"


def extraer_ingreso(mensaje: str) -> dict:
    """Extrae monto, descripción y medio de un mensaje de ingreso."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_INGRESO.format(mensaje=mensaje)],
    )
    texto = response.text.strip()
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    return json.loads(texto)


def extraer_gastos(mensaje: str) -> tuple[list[dict], str]:
    """
    Extrae lista de gastos y la fecha detectada del mensaje.
    Retorna (gastos, fecha_str) donde fecha_str es YYYY-MM-DD.
    """
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_GASTOS.format(mensaje=mensaje, hoy=hoy)],
    )
    texto = response.text.strip()
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    data = json.loads(texto)
    # Soporta tanto el nuevo formato {fecha, gastos} como lista directa (retrocompatible)
    if isinstance(data, dict):
        gastos = data.get("gastos", [])
        fecha = data.get("fecha", hoy)
    else:
        gastos = data if isinstance(data, list) else []
        fecha = hoy
    return gastos, fecha


PROMPT_EDICION = """
Eres un asistente de finanzas personales para usuarios en Perú.

El usuario quiere editar una transacción y escribió: "{mensaje}"

Extrae los datos que mencionó y responde ÚNICAMENTE con un JSON válido:
{{
  "monto": 50.00,
  "descripcion": "comida de gato",
  "categoria": "Mascotas"
}}

Categorías disponibles: Comida, Supermercado, Transporte, Servicios, Salud, Educacion, Ropa, Entretenimiento, Tecnologia, Finanzas, Mascotas, Belleza, Hogar, Otros

Reglas:
- Si no se menciona el monto, usa 0
- Si no se menciona descripción, usa ""
- Si no puedes determinar la categoría, infierela de la descripción
- El monto debe ser un número decimal sin S/
"""


def extraer_edicion(mensaje: str) -> dict:
    """Extrae monto, descripción y categoría de un mensaje de edición en lenguaje natural."""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_EDICION.format(mensaje=mensaje)],
    )
    texto = response.text.strip()
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    return json.loads(texto)
