"""
audio.py — FinanzasBot v3.1
Transcribe notas de voz de Telegram (OGG/Opus) con Qwen ASR.
"""

import base64
import pathlib

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_ASR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)


def transcribir_audio(file_path: str) -> str | None:
    """OGG/Opus de Telegram -> texto. None si no se pudo transcribir.

    Telegram siempre manda notas de voz en OGG/Opus, así que el formato va fijo
    (no hace falta detectar la extensión como en ocr.py).
    """
    audio_bytes = pathlib.Path(file_path).read_bytes()
    b64 = base64.b64encode(audio_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_ASR,
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "El audio está en español."}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/ogg;base64,{b64}",
                                "format": "ogg",
                            },
                        },
                    ],
                },
            ],
        )
        texto = response.choices[0].message.content
        return texto.strip() if isinstance(texto, str) and texto.strip() else None
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")
        return None
