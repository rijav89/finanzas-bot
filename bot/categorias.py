# categorias.py — FinanzasBot v3.1
# Categorización con Qwen (OpenAI-compatible API)

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_TEXT

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

CATEGORIAS_DISPONIBLES = [
    "Comida", "Supermercado", "Transporte", "Servicios", "Salud",
    "Educacion", "Ropa", "Entretenimiento", "Tecnologia", "Finanzas",
    "Mascotas", "Belleza", "Hogar", "Otros",
]

PROMPT_CATEGORIA = """Eres un asistente de finanzas personales para usuarios en Perú.
Basándote en la siguiente descripción de un gasto, clasifícalo en UNA de estas categorías:

{categorias}

Descripción del gasto: "{descripcion}"

Responde ÚNICAMENTE con el nombre exacto de la categoría, sin explicación ni texto adicional."""


def clasificar_gasto(descripcion: str) -> str:
    if not descripcion or descripcion.strip().lower() in [
        "sin descripcion", "sin descripción", "", "."
    ]:
        return "Otros"

    prompt = PROMPT_CATEGORIA.format(
        categorias="\n".join(f"- {c}" for c in CATEGORIAS_DISPONIBLES),
        descripcion=descripcion.strip(),
    )

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        categoria = response.choices[0].message.content.strip()

        for c in CATEGORIAS_DISPONIBLES:
            if c.lower() == categoria.lower():
                return c
    except Exception as e:
        print(f"[CATEGORIA ERROR] {e}")

    return "Otros"
