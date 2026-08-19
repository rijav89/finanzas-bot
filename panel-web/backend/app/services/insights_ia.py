"""Llamada a Qwen para convertir el resumen numérico en insights legibles.

Vive fuera del request path: solo la usa el job semanal. Ninguna petición del usuario
espera nunca por el modelo.
"""
import asyncio
import json
from datetime import date

from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.insights import MAX_INSIGHTS, RespuestaInsights

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

PROMPT = """Sos un analista de finanzas personales para un usuario en Perú. La moneda es el sol (S/).

Estos son sus datos reales, ya calculados. No inventes cifras: usá solo estas.

{resumen}

Devolvé como máximo {maximo} observaciones útiles y accionables, ordenadas de más a menos importante.
Reglas:
- Cada observación debe apoyarse en una cifra concreta de los datos de arriba.
- Nada de obviedades ("gastaste plata este mes") ni de consejos genéricos de ahorro.
- Si algo subió o bajó, decí cuánto y contra qué.
- Escribí en español rioplatense neutro, en segunda persona, directo y sin moralizar.
- severidad: 'critico' solo si hay riesgo real (presupuesto excedido, saldo en rojo,
  gastás más de lo que ingresa); 'atencion' si conviene mirarlo; 'info' para el resto.
- Si los datos no dan para {maximo}, devolvé menos. Preferible poco y bueno.

Respondé SOLO con JSON válido, sin markdown ni texto alrededor:
{{"insights": [{{"tipo": "patron_gasto|alerta_presupuesto|tendencia|recomendacion",
  "severidad": "info|atencion|critico", "titulo": "<máx 90 caracteres>",
  "detalle": "<máx 320 caracteres>", "categoria": "<categoría o null>",
  "metrica": "<cifra que lo sostiene, ej. S/ 450.00, o null>",
  "delta_pct": <número o null>}}]}}"""


def _plata(v: float) -> str:
    return f"S/ {v:,.2f}"


def formatear_resumen(datos: dict) -> str:
    """El resumen numérico como texto compacto. Es lo único que ve el modelo."""
    lineas: list[str] = []

    lineas.append("HISTORIA MENSUAL")
    for h in datos["historia"]:
        etiqueta = f"{MESES_ES[h['mes'] - 1]} {h['anio']}"
        ahorro = h["ingresos"] - h["gastos"]
        lineas.append(
            f"- {etiqueta}: ingresos {_plata(h['ingresos'])}, gastos {_plata(h['gastos'])}, "
            f"diferencia {_plata(ahorro)}"
        )

    actual = datos["historia"][-1]
    promedio = datos["promedio_categorias_previos"]
    lineas.append("\nGASTOS DEL MES EN CURSO POR CATEGORÍA (vs promedio de los meses previos)")
    if not actual["por_categoria"]:
        lineas.append("- sin gastos registrados todavía")
    for cat, total in sorted(actual["por_categoria"].items(), key=lambda x: -x[1]):
        ref = promedio.get(cat)
        if ref:
            delta = (total - ref) / ref * 100
            lineas.append(f"- {cat}: {_plata(total)} (promedio {_plata(ref)}, {delta:+.0f}%)")
        else:
            lineas.append(f"- {cat}: {_plata(total)} (sin antecedente en meses previos)")

    solo_antes = [c for c in promedio if c not in actual["por_categoria"]]
    if solo_antes:
        lineas.append(f"- categorías con gasto antes y no este mes: {', '.join(solo_antes)}")

    lineas.append("\nPRESUPUESTOS DEL MES")
    if not datos["presupuestos"]:
        lineas.append("- el usuario no definió presupuestos")
    for p in datos["presupuestos"]:
        pct = p["gastado"] / p["limite"] * 100 if p["limite"] else 0
        lineas.append(
            f"- {p['categoria']}: gastó {_plata(p['gastado'])} de {_plata(p['limite'])} ({pct:.0f}%)"
        )

    lineas.append("\nSITUACIÓN GENERAL")
    lineas.append(f"- saldo total en cuentas: {_plata(datos['saldo_total'])}")
    lineas.append(f"- deuda pendiente: {_plata(datos['deuda_pendiente'])}")
    rec = datos["recurrentes"]
    lineas.append(
        f"- pagos recurrentes mensuales: {rec['cantidad']} por {_plata(rec['total_mensual'])}"
    )
    lineas.append(f"- diferencia del mes en curso: {_plata(datos['ahorro_mes'])}")

    return "\n".join(lineas)


def _limpiar(bruto: str) -> str:
    """El modelo a veces envuelve el JSON en un bloque de markdown."""
    return bruto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def _cliente():
    from openai import OpenAI

    s = get_settings()
    return OpenAI(api_key=s.dashscope_api_key, base_url=s.qwen_base_url)


async def generar(datos: dict, intentos: int = 2) -> tuple[RespuestaInsights, int]:
    """Devuelve los insights validados y los tokens consumidos.

    Reintenta una vez: si el modelo devuelve JSON inválido suele acertar al segundo
    tiro, y una llamada de más es más barata que una semana sin insights.
    """
    settings = get_settings()
    prompt = PROMPT.format(resumen=formatear_resumen(datos), maximo=MAX_INSIGHTS)
    tokens = 0
    ultimo_error: Exception | None = None

    for intento in range(intentos):
        respuesta = await asyncio.to_thread(
            lambda: _cliente().chat.completions.create(
                model=settings.qwen_model_text,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
        )
        tokens += getattr(respuesta.usage, "total_tokens", 0) or 0
        try:
            return RespuestaInsights(**json.loads(_limpiar(respuesta.choices[0].message.content))), tokens
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            ultimo_error = e
            print(f"[INSIGHTS] respuesta inválida (intento {intento + 1}): {e}")

    raise ValueError(f"El modelo no devolvió un JSON válido: {ultimo_error}")


def periodo_de(datos: dict) -> tuple[date, date]:
    return datos["periodo"]["desde"], datos["periodo"]["hasta"]
