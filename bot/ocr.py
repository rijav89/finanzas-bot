"""
ocr.py — FinanzasBot v3.1
Usa Qwen VL OCR (Alibaba Cloud) con OpenAI-compatible API.
"""

import json
import base64
import pathlib
from datetime import date

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_OCR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

PROMPT = """Analiza esta imagen financiera peruana. Puede ser:
(a) un voucher de UN SOLO pago (Yape, Plin o depósito/transferencia bancaria), o
(b) una captura de un HISTORIAL con varios movimientos listados (lista de Yape,
    estado de cuenta, historial de transacciones de una app de banco).

Responde SOLO con un array JSON, sin markdown ni explicaciones — incluso si hay
un solo movimiento, va dentro de un array de un elemento.

Formato exacto de cada elemento:
{
  "monto": "85.50",
  "medio": "Yape",
  "destinatario": "Juan Perez",
  "descripcion": "concepto visible, ej. 'Yape a Rosa' o 'Deposito'",
  "fecha": "2026-03-19"
}

Reglas:
- Si es un voucher de un solo pago, el array tiene un solo elemento.
- Si es un historial con una tabla o lista, incluí TODOS los movimientos que
  veas, uno por elemento, en el mismo orden en que aparecen en la imagen.
- Si varios movimientos comparten una fecha visible como encabezado de sección
  (ej. "Hoy", "15 de agosto"), aplicá esa fecha a cada uno de esos movimientos.
- Si el año no aparece en la imagen, usá el año actual.
- monto: solo el número, sin S/. Si no se detecta, usa "No detectado".
- medio: "Yape", "Plin", "Transferencia" o "No identificado".
- destinatario: nombre o entidad visible, o "No detectado".
- descripcion: lo que diga el concepto/glosa del movimiento, o "" si no hay nada.
- fecha: formato YYYY-MM-DD, o "No detectada" si de verdad no se puede inferir.
- No inventes datos: un campo que no se ve va con su valor por defecto.
"""


def procesar_voucher(file_path: str) -> list[dict]:
    """Lee una imagen y devuelve la lista de movimientos que encuentra.

    Un voucher de un solo pago devuelve una lista de longitud 1 — así el
    llamador no tiene que distinguir "un voucher" de "una lista de uno" como
    dos casos separados.
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

        # Salvavidas: si el modelo no siguió la instrucción del array y devolvió
        # un objeto suelto (más probable con un voucher de un solo pago), se
        # envuelve igual — el llamador siempre recibe una lista.
        movimientos = data if isinstance(data, list) else [data]

        return [_normalizar(m) for m in movimientos]

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return []


def _normalizar(m: dict) -> dict:
    fecha = m.get("fecha") or "No detectada"
    if fecha == "No detectada":
        # Sin corrección de año ambiguo (fuera de alcance): si no hay fecha
        # legible, se asume hoy y el usuario corrige a mano si hace falta.
        fecha = date.today().strftime("%Y-%m-%d")
    return {
        "monto": m.get("monto") or "No detectado",
        "medio": m.get("medio") or "No identificado",
        "destinatario": m.get("destinatario") or "No detectado",
        "descripcion": m.get("descripcion") or "",
        "fecha": fecha,
    }
