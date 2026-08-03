"""
ocr.py — FinanzasBot v2.3
Usa Gemini 1.5/2.5 Flash con Structured Outputs (Pydantic).
"""

import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import pathlib
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

class VoucherInfo(BaseModel):
    monto: str = Field(description="Solo el numero, ej. 85.50. Si no se detecta, usa 'No detectado'. No incluyas S/.")
    medio: str = Field(description="Yape, Plin o No identificado")
    destinatario: str = Field(description="Nombre del destinatario o No detectado")
    fecha: str = Field(description="Fecha de la operacion o No detectada")

PROMPT = "Analiza esta imagen de un voucher de pago (Yape o Plin de Peru). Extrae los datos segun el esquema solicitado."

def procesar_voucher(file_path: str) -> tuple[str, str, str, str]:
    """
    Procesa un voucher usando Gemini y retorna monto, medio, destinatario, fecha.
    """
    image_bytes = pathlib.Path(file_path).read_bytes()

    suffix = pathlib.Path(file_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VoucherInfo,
            temperature=0.1,
        )
    )

    try:
        # En caso el SDK retorne el objeto parseado, pero aseguramos con json manual
        data = json.loads(response.text.strip())
        monto = data.get("monto", "No detectado")
        medio = data.get("medio", "No identificado")
        destinatario = data.get("destinatario", "No detectado")
        fecha = data.get("fecha", "No detectada")
    except Exception:
        # Fallback de seguridad
        monto = "No detectado"
        medio = "No identificado"
        destinatario = "No detectado"
        fecha = "No detectada"

    return monto, medio, destinatario, fecha
