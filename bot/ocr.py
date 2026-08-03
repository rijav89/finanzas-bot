"""
ocr.py — FinanzasBot v3.1
Usa Qwen VL OCR (Alibaba Cloud) con OpenAI-compatible API.
"""

import json
import base64
import pathlib
from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_OCR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

PROMPT = """Analiza esta imagen de un voucher de pago (Yape o Plin de Peru).
Extrae los datos y responde SOLO con un JSON válido, sin markdown ni explicaciones.

Formato exacto:
{
  "monto": "85.50",
  "medio": "Yape",
  "destinatario": "Juan Perez",
  "fecha": "2026-03-19"
}

Reglas:
- monto: solo el número, sin S/. Si no se detecta usa "No detectado"
- medio: "Yape", "Plin" o "No identificado"
- destinatario: nombre del destinatario o "No detectado"
- fecha: formato YYYY-MM-DD o "No detectada"
"""

def procesar_voucher(file_path: str) -> tuple[str, str, str, str]:
    """
    Procesa un voucher usando Qwen VL OCR y retorna monto, medio, destinatario, fecha.
    """
    image_bytes = pathlib.Path(file_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    suffix = pathlib.Path(file_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_OCR,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        monto       = data.get("monto", "No detectado")
        medio       = data.get("medio", "No identificado")
        destinatario = data.get("destinatario", "No detectado")
        fecha       = data.get("fecha", "No detectada")

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        monto       = "No detectado"
        medio       = "No identificado"
        destinatario = "No detectado"
        fecha       = "No detectada"

    return monto, medio, destinatario, fecha
