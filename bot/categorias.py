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

# Respaldo si la base no responde. El catálogo vigente se lee de la tabla
# `categorias`, que es la que el usuario edita desde el panel web.
CATEGORIAS_DISPONIBLES = list(CATEGORIAS_GASTO)
CATEGORIAS_INGRESO_DISPONIBLES = list(CATEGORIAS_INGRESO)

_BASE = {"gasto": CATEGORIAS_GASTO, "ingreso": CATEGORIAS_INGRESO}
_TTL_CACHE = 300  # 5 min: cambiar una categoría en el panel tarda eso en verse acá
_cache: dict = {}


def catalogo(tipo: str, usuario_id: int | None = None) -> dict:
    """Categorías vigentes del usuario, como {nombre: pista}.

    Las de sistema traen su pista; las que el usuario creó en el panel entran sin
    pista (el nombre ya dice bastante). Si la consulta falla se usa el respaldo:
    quedarse sin clasificar es peor que clasificar con una lista un poco vieja.
    """
    base = _BASE[tipo]
    if usuario_id is None:
        return dict(base)

    import time

    clave = (usuario_id, tipo)
    guardado = _cache.get(clave)
    if guardado and time.monotonic() - guardado[0] < _TTL_CACHE:
        return guardado[1]

    try:
        from db import obtener_categorias  # import diferido: evita ciclo con db.py

        nombres = obtener_categorias(usuario_id, tipo)
    except Exception as e:
        print(f"[CATALOGO ERROR] {e}")
        return dict(base)

    if not nombres:
        return dict(base)

    resultado = {n: base.get(n, "") for n in nombres}
    _cache[clave] = (time.monotonic(), resultado)
    return resultado

_SIN_DESCRIPCION = {"sin descripcion", "sin descripción", "", ".", "ingreso"}

PROMPT_CATEGORIA = """Eres un asistente de finanzas personales para usuarios en Perú.
Clasifica el siguiente {que} en UNA de estas categorías:

{categorias}

Descripción: "{descripcion}"

Responde ÚNICAMENTE con el nombre exacto de la categoría, sin explicación ni texto adicional."""


def _clasificar(descripcion: str, opciones: dict, que: str, defecto: str) -> str:
    if not descripcion or descripcion.strip().lower() in _SIN_DESCRIPCION:
        return defecto

    prompt = PROMPT_CATEGORIA.format(
        que=que,
        categorias="\n".join(
            f"- {nombre}: {pista}" if pista else f"- {nombre}"
            for nombre, pista in opciones.items()
        ),
        descripcion=descripcion.strip(),
    )

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        respuesta = response.choices[0].message.content.strip()

        for c in opciones:
            if c.lower() == respuesta.lower():
                return c
    except Exception as e:
        print(f"[CATEGORIA ERROR] {e}")

    return defecto


def clasificar_gasto(descripcion: str, usuario_id: int | None = None) -> str:
    return _clasificar(descripcion, catalogo("gasto", usuario_id), "gasto", "Otros")


def clasificar_ingreso(descripcion: str, usuario_id: int | None = None) -> str:
    """Los ingresos tienen su propio catálogo: pasarlos por el de gastos los
    mandaba siempre a 'Otros' y dejaba el panel sin poder mostrar de dónde vino."""
    return _clasificar(
        descripcion, catalogo("ingreso", usuario_id), "ingreso", "Otros ingresos"
    )
