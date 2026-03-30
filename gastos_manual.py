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
    TRANSFERIR = "TRANSFERIR"
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
IMPORTANTE: Si el mensaje es un saludo (como "hola", "buenos días") o charla genérica no relacionada a finanzas, elige estrictamente "FUERA_DE_TEMA". Solo debes elegir otras intenciones si hay una consulta o acción financiera clara.
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
    cuenta_destino: str = Field(description="Nombre de la cuenta destino inferida (case insensitive). Usa 'Principal' si no deduces otra de la lista proporcionada.")
    fecha: str = Field(description="Fecha detectada en formato YYYY-MM-DD. Adapta la fecha al mensaje respecto a hoy (ej. 'ayer me pagaron').")

PROMPT_INGRESO = """
Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae los datos del ingreso mencionado según el esquema.
"""

def extraer_ingreso(mensaje: str, cuentas=None) -> dict:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_INGRESO.format(mensaje=mensaje, hoy=hoy, cuentas=cuentas_str)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IngresoResponse,
            temperature=0.0
        )
    )
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"monto": 0, "descripcion": "Ingreso desconocido", "medio": "No especificado", "cuenta_destino": "Principal", "fecha": hoy}

# --- 3. Gastos ---
class GastoItem(BaseModel):
    monto: float = Field(description="Monto del gasto. Número decimal.")
    descripcion: str = Field(description="Breve descripción, ej. menú, taxi.")
    categoria: str = Field(description="Categoría permitida: Comida, Supermercado, Transporte, Servicios, Salud, Educacion, Ropa, Entretenimiento, Tecnologia, Finanzas, Mascotas, Belleza, Hogar, Otros")
    cuenta_origen: str = Field(description="Nombre de la cuenta origen inferida (case insensitive). Usa 'Principal' si no deduces otra de la lista proporcionada.")

class GastosResponse(BaseModel):
    fecha: str = Field(description="Fecha detectada en formato YYYY-MM-DD. Modifica la fecha según lo mencione el usuario (ej. ayer resta 1).")
    gastos: list[GastoItem] = Field(description="Lista de gastos extraídos.")

PROMPT_GASTOS = """
Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae la fecha y la lista de gastos mencionados según el esquema.
Regla: Adapta 'fecha' según mencione el usuario (ej. "ayer", "el martes"). Si no menciona, usa {hoy}.
"""

def extraer_gastos(mensaje: str, cuentas=None) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_GASTOS.format(mensaje=mensaje, hoy=hoy, cuentas=cuentas_str)],
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

""" --- 3.5 Transferencia --- """
class TransferenciaResponse(BaseModel):
    monto: float = Field(description="El monto a transferir. 0 si no se infiere.")
    cuenta_origen: str = Field(description="Nombre de la cuenta origen (case insensitive). Usa 'Principal' si no deduces.")
    cuenta_destino: str = Field(description="Nombre de la cuenta destino (case insensitive).")

PROMPT_TRANSFERENCIA = """
Cuentas disponibles: {cuentas}
Usuario quiere hacer una transferencia: "{mensaje}"
Extrae origen, destino y monto según el esquema. Intenta inferir de 'Cuentas disponibles'.
"""

def extraer_transferencia(mensaje: str, cuentas=None) -> dict:
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT_TRANSFERENCIA.format(mensaje=mensaje, cuentas=cuentas_str)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TransferenciaResponse,
            temperature=0.0
        )
    )
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {"monto": 0, "cuenta_origen": "", "cuenta_destino": ""}

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
