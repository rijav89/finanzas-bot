"""
ocr.py — FinanzasBot v3.1
Usa Qwen VL OCR (Alibaba Cloud) con OpenAI-compatible API.
"""

import json
import base64
import pathlib
import re
from datetime import date, datetime

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


MONTO_NO_DETECTADO = "No detectado"

# El prompt pide YYYY-MM-DD, pero un modelo no es un parser: devuelve
# "15/08/2026" o "2026-8-5" cuando eso es lo que dice la imagen. Esa fecha
# termina en un BETWEEN de SQL y en un strptime, así que se normaliza acá —
# es el único punto por el que pasa todo lo que sale del OCR.
_FORMATOS_FECHA = (
    "%Y-%m-%d",   # el formato pedido (tolera "2026-8-5")
    "%d/%m/%Y",   # el formato peruano de toda la vida
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
)


def normalizar_fecha(valor) -> str:
    """Devuelve una fecha YYYY-MM-DD siempre válida.

    Si no se puede interpretar, se asume hoy — el mismo criterio que ya tenía
    el caso "No detectada" (sin corrección de año ambiguo: fuera de alcance).
    """
    hoy = date.today().strftime("%Y-%m-%d")
    if valor is None:
        return hoy
    texto = str(valor).strip()
    if not texto or texto == "No detectada":
        return hoy
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return hoy


def normalizar_monto(valor) -> str:
    """Devuelve el monto como string apto para float(), o "No detectado".

    El modelo tiene la costumbre de copiar lo que ve: "S/ 85.50", "1,250.00",
    "1.250,00". Aguas abajo hay tres float() sin protección (dedupe, el teclado
    del checklist y el INSERT), así que la limpieza va acá.
    """
    if valor is None:
        return MONTO_NO_DETECTADO
    texto = str(valor).strip()
    if not texto:
        return MONTO_NO_DETECTADO

    limpio = re.sub(r"[^0-9,.\-]", "", texto)   # fuera "S/", espacios, letras
    negativo = limpio.startswith("-")
    limpio = limpio.replace("-", "")
    if not any(c.isdigit() for c in limpio):
        return MONTO_NO_DETECTADO

    if "," in limpio and "." in limpio:
        # Conviven los dos: el que va más a la derecha es el decimal.
        corte = max(limpio.rfind(","), limpio.rfind("."))
        limpio = re.sub(r"[.,]", "", limpio[:corte]) + "." + re.sub(r"[.,]", "", limpio[corte + 1:])
    elif "," in limpio:
        cola = limpio.rsplit(",", 1)[1]
        cabeza = limpio[:limpio.rfind(",")]
        if len(cola) == 3 and cabeza:
            limpio = limpio.replace(",", "")     # "1,250" son mil doscientos
        else:
            limpio = limpio.replace(",", ".")    # "85,50" son ochenta y cinco con cincuenta
    elif limpio.count(".") > 1:
        corte = limpio.rfind(".")
        limpio = limpio[:corte].replace(".", "") + limpio[corte:]

    try:
        numero = float(limpio)
    except ValueError:
        return MONTO_NO_DETECTADO
    return f"{-numero if negativo else numero:.2f}"


def _normalizar(m: dict) -> dict:
    return {
        "monto": normalizar_monto(m.get("monto")),
        "medio": m.get("medio") or "No identificado",
        "destinatario": m.get("destinatario") or "No detectado",
        "descripcion": m.get("descripcion") or "",
        "fecha": normalizar_fecha(m.get("fecha")),
    }
