"""
ocr.py — FinanzasBot v2.3
Usa Gemini 1.5 Flash con la librería actualizada google-genai.

SETUP:
    pip uninstall google-generativeai -y
    pip install google-genai pillow
"""

import json
from google import genai
from google.genai import types
from PIL import Image
import pathlib
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT = """
Analiza esta imagen de un voucher de pago (Yape o Plin de Peru).
Extrae los siguientes datos y responde UNICAMENTE con un JSON valido, sin texto adicional:

{
  "monto": "solo el numero, ejemplo: 85.50",
  "medio": "Yape o Plin o No identificado",
  "destinatario": "nombre del destinatario o No detectado",
  "fecha": "fecha de la operacion o No detectada"
}

Si no puedes leer algun campo con certeza, usa "No detectado".
No incluyas el simbolo S/ en el monto.
"""


def procesar_voucher(file_path: str) -> tuple[str, str, str, str]:
    """
    Procesa un voucher usando Gemini 1.5 Flash (google-genai).

    Retorna:
        monto        (str): Ej. "85.50"
        medio        (str): "Yape", "Plin" o "No identificado"
        destinatario (str): Nombre del destinatario
        fecha        (str): Fecha de la operacion
    """
    image_bytes = pathlib.Path(file_path).read_bytes()

    # Detectar tipo de imagen
    suffix = pathlib.Path(file_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            PROMPT,
        ],
    )

    texto = response.text.strip()

    # Limpia posibles bloques ```json ... ```
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    data = json.loads(texto)

    monto        = data.get("monto", "No detectado")
    medio        = data.get("medio", "No identificado")
    destinatario = data.get("destinatario", "No detectado")
    fecha        = data.get("fecha", "No detectada")

    return monto, medio, destinatario, fecha
