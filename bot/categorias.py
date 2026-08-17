# categorias.py — FinanzasBot v3.1
# Categorización con Qwen (OpenAI-compatible API)

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_TEXT

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

# Cada categoría lleva una pista de una línea: con solo el nombre, el modelo
# confunde sistemáticamente Servicios con Hogar y Tecnologia con Suscripciones.
# El costo son ~250 tokens extra por llamada; la precisión los paga.
CATEGORIAS_GASTO = {
    "Comida": "restaurantes, delivery, almuerzos, cafes, snacks",
    "Supermercado": "compras de despensa y abarrotes para la casa",
    "Vivienda": "alquiler, hipoteca, arbitrios, mantenimiento del edificio",
    "Servicios": "luz, agua, gas, internet, celular, cable",
    "Transporte y vehiculo": "taxi, bus, combustible, cochera, mantenimiento del auto, SOAT",
    "Salud": "farmacia, consultas, examenes, seguro medico",
    "Educacion": "matriculas, pensiones, cursos, libros, utiles",
    "Ropa": "prendas, calzado, accesorios de vestir",
    "Entretenimiento": "cine, salidas, conciertos, juegos, paseos",
    "Suscripciones": "Netflix, Spotify, iCloud, gimnasio, apps de pago mensual",
    "Tecnologia": "celulares, laptops, accesorios y reparaciones de equipos",
    "Finanzas": "comisiones bancarias, intereses, seguros, inversiones",
    "Mascotas": "comida de mascota, veterinario, accesorios",
    "Belleza": "peluqueria, cosmeticos, cuidado personal",
    "Hogar": "muebles, electrodomesticos, decoracion, limpieza, reparaciones",
    "Regalos": "regalos que das, donaciones, celebraciones",
    "Impuestos": "SUNAT, tributos, notaria, tramites y multas",
    "Otros": "solo si ninguna de las anteriores encaja",
}

CATEGORIAS_INGRESO = {
    "Sueldo": "sueldo, salario, planilla, gratificacion, CTS",
    "Freelance": "trabajos independientes, honorarios, recibo por honorarios",
    "Negocio": "ventas y ganancias de negocio propio",
    "Regalo recibido": "dinero que te regalaron o te dieron",
    "Reembolso": "devoluciones, reintegros, dinero que te devuelven",
    "Intereses": "rendimientos, dividendos, intereses de ahorros o inversiones",
    "Otros ingresos": "solo si ninguna de las anteriores encaja",
}

# Los prompts de gastos_manual.py arman su enum con estas listas.
CATEGORIAS_DISPONIBLES = list(CATEGORIAS_GASTO)
CATEGORIAS_INGRESO_DISPONIBLES = list(CATEGORIAS_INGRESO)

_SIN_DESCRIPCION = {"sin descripcion", "sin descripción", "", ".", "ingreso"}

PROMPT_CATEGORIA = """Eres un asistente de finanzas personales para usuarios en Perú.
Clasifica el siguiente {que} en UNA de estas categorías:

{categorias}

Descripción: "{descripcion}"

Responde ÚNICAMENTE con el nombre exacto de la categoría, sin explicación ni texto adicional."""


def _clasificar(descripcion: str, catalogo: dict[str, str], que: str, defecto: str) -> str:
    if not descripcion or descripcion.strip().lower() in _SIN_DESCRIPCION:
        return defecto

    prompt = PROMPT_CATEGORIA.format(
        que=que,
        categorias="\n".join(f"- {nombre}: {pista}" for nombre, pista in catalogo.items()),
        descripcion=descripcion.strip(),
    )

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        respuesta = response.choices[0].message.content.strip()

        for c in catalogo:
            if c.lower() == respuesta.lower():
                return c
    except Exception as e:
        print(f"[CATEGORIA ERROR] {e}")

    return defecto


def clasificar_gasto(descripcion: str) -> str:
    return _clasificar(descripcion, CATEGORIAS_GASTO, "gasto", "Otros")


def clasificar_ingreso(descripcion: str) -> str:
    """Los ingresos tienen su propio catálogo: pasarlos por el de gastos los
    mandaba siempre a 'Otros' y dejaba el panel sin poder mostrar de dónde vino."""
    return _clasificar(descripcion, CATEGORIAS_INGRESO, "ingreso", "Otros ingresos")
