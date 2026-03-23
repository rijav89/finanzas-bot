"""
gastos_manual.py — FinanzasBot v2.8
Detecta la intención y extrae datos con Gemini Structured Outputs.
"""

import json
from enum import Enum
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 1. Intención ---
class IntencionEnum(str, Enum):
    REGISTRAR_GASTOS = "REGISTRAR_GASTOS"
    INICIAR_REGISTRO = "INICIAR_REGISTRO"
    REGISTRAR_INGRESO = "REGISTRAR_INGRESO"
    VER_RESUMEN = "VER_RESUMEN"
    VER_CATEGORIAS = "VER_CATEGORIAS"
    VER_HISTORIAL = "VER_HISTORIAL"
    VER_SALDO = "VER_SALDO"
    EXPORTAR = "EXPORTAR"
    AYUDA = "AYUDA"
    FUERA_DE_TEMA = "FUERA_DE_TEMA"

class IntencionResponse(BaseModel):
    intencion: IntencionEnum = Field(description="La categoría de intención detectada.")

PROMPT_INTENCION = """
Eres un asistente de finanzas personales para usuarios en Perú llamado FinanzasBot.
El usuario escribió: "{mensaje}"
Clasifica la intención en las opciones permitidas en el esquema.
"""

def detectar_intencion(mensaje: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_INTENCION.format(mensaje=mensaje)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IntencionResponse,
            temperature=0.0
        )
    )
    try:
        data = json.loads(response.text.strip())
        return data.get("intencion", "FUERA_DE_TEMA")
    except Exception:
        return "FUERA_DE_TEMA"

# --- 2. Ingreso ---
class IngresoResponse(BaseModel):
    monto: float = Field(description="El monto del ingreso. Si no se menciona, usa 0.")
    descripcion: str = Field(description="Descripción del ingreso, ej. sueldo. Vacio si no hay.")
    medio: str = Field(description="Medio de pago: Yape, Plin, Transferencia, Efectivo, Depósito, o No especificado.")

PROMPT_INGRESO = """
Eres un asistente de finanzas personales.
Usuario: "{mensaje}"
Extrae los datos del ingreso mencionado según el esquema.
"""

def extraer_ingreso(mensaje: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_INGRESO.format(mensaje=mensaje)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IngresoResponse,
            temperature=0.0
        )
    )
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"monto": 0, "descripcion": "Ingreso desconocido", "medio": "No especificado"}

# --- 3. Gastos ---
class GastoItem(BaseModel):
    monto: float = Field(description="Monto del gasto. Número decimal.")
    descripcion: str = Field(description="Breve descripción, ej. menú, taxi.")
    categoria: str = Field(description="Categoría permitida: Comida, Supermercado, Transporte, Servicios, Salud, Educacion, Ropa, Entretenimiento, Tecnologia, Finanzas, Mascotas, Belleza, Hogar, Otros")

class GastosResponse(BaseModel):
    fecha: str = Field(description="Fecha detectada en formato YYYY-MM-DD. Modifica la fecha según lo mencione el usuario (ej. ayer resta 1).")
    gastos: list[GastoItem] = Field(description="Lista de gastos extraídos.")

PROMPT_GASTOS = """
Hoy es {hoy}.
Usuario: "{mensaje}"
Extrae la fecha y la lista de gastos mencionados según el esquema.
Regla: Adapta 'fecha' según mencione el usuario (ej. "ayer", "el martes"). Si no menciona, usa {hoy}.
"""

def extraer_gastos(mensaje: str) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_GASTOS.format(mensaje=mensaje, hoy=hoy)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GastosResponse,
            temperature=0.0
        )
    )
    try:
        data = json.loads(response.text.strip())
        gastos = data.get("gastos", [])
        fecha = data.get("fecha", hoy)
        return gastos, fecha
    except Exception:
        return [], hoy

# --- 4. Edición ---
class EdicionResponse(BaseModel):
    monto: float = Field(description="Nuevo monto. 0 si no se menciona.")
    descripcion: str = Field(description="Nueva descripción. Vacio si no.")
    categoria: str = Field(description="Nueva categoria de la lista (Comida, Supermercado, etc.). Vacio si falla.")

PROMPT_EDICION = """
Usuario quiere editar un gasto: "{mensaje}"
Extrae monto, descripcion y categoria según el esquema.
"""

def extraer_edicion(mensaje: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_EDICION.format(mensaje=mensaje)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EdicionResponse,
            temperature=0.0
        )
    )
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"monto": 0, "descripcion": "", "categoria": ""}
