# categorias.py — FinanzasBot v2.4
# Categorización con IA usando Gemini

from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

CATEGORIAS_DISPONIBLES = [
    "Comida",
    "Supermercado",
    "Transporte",
    "Servicios",
    "Salud",
    "Educacion",
    "Ropa",
    "Entretenimiento",
    "Tecnologia",
    "Finanzas",
    "Mascotas",
    "Belleza",
    "Hogar",
    "Otros",
]

PROMPT_CATEGORIA = """
Eres un asistente de finanzas personales para usuarios en Perú.
Basándote en la siguiente descripción de un gasto, clasifícalo en UNA de estas categorías:

{categorias}

Descripción del gasto: "{descripcion}"

Responde ÚNICAMENTE con el nombre exacto de la categoría, sin explicación ni texto adicional.
"""


def clasificar_gasto(descripcion: str) -> str:
    """
    Clasifica un gasto usando Gemini IA basándose en la descripción.
    Si la descripción está vacía o es genérica, retorna "Otros".
    """
    if not descripcion or descripcion.strip().lower() in [
        "sin descripcion", "sin descripción", "", "."
    ]:
        return "Otros"

    prompt = PROMPT_CATEGORIA.format(
        categorias="\n".join(f"- {c}" for c in CATEGORIAS_DISPONIBLES),
        descripcion=descripcion.strip(),
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
    )

    categoria = response.text.strip()

    # Validar que la respuesta sea una categoría válida
    for c in CATEGORIAS_DISPONIBLES:
        if c.lower() == categoria.lower():
            return c

    return "Otros"
