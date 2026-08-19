"""Job semanal: genera los insights de cada usuario con qwen-plus.

Proceso corto e independiente — arranca, trabaja y muere. No comparte proceso con la
API, así que un pico de memoria acá no puede tumbar el panel.

    python -m jobs.generar_insights            # todos los usuarios vinculados
    python -m jobs.generar_insights --usuario 1
    python -m jobs.generar_insights --seco     # muestra el prompt, no llama al modelo

La fecha se toma en hora de Lima, no en UTC: el servidor corre en UTC y a las 20:00
de Lima allá ya es el día siguiente, lo que correría la ventana del mes.
"""
import argparse
import asyncio
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, text  # noqa: E402

from app.analytics.insights import datos_para_insights  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import async_session  # noqa: E402
from app.models import InsightIA  # noqa: E402
from app.services import insights_ia  # noqa: E402

LIMA = ZoneInfo("America/Lima")


def hoy_lima() -> date:
    return datetime.now(LIMA).date()


async def usuarios_objetivo(session, usuario_id: int | None) -> list[int]:
    if usuario_id is not None:
        return [usuario_id]
    # Solo quienes usan el panel: el insight se lee ahí, no en Telegram
    filas = await session.execute(text("SELECT usuario_id FROM vinculos_auth ORDER BY usuario_id"))
    return [f[0] for f in filas.all()]


async def procesar(usuario_id: int, hoy: date, seco: bool) -> str:
    async with async_session() as session:
        datos = await datos_para_insights(session, usuario_id, hoy)
        if datos is None:
            return f"usuario {usuario_id}: sin historia suficiente, se omite"

        if seco:
            print("─" * 70)
            print(insights_ia.formatear_resumen(datos))
            print("─" * 70)
            return f"usuario {usuario_id}: prompt mostrado (modo seco, no se llamó al modelo)"

        respuesta, tokens = await insights_ia.generar(datos)
        desde, hasta = insights_ia.periodo_de(datos)
        modelo = get_settings().qwen_model_text

        async with session.begin():
            # Volver a correr el job para el mismo período reemplaza, no acumula
            await session.execute(
                delete(InsightIA).where(
                    InsightIA.usuario_id == usuario_id,
                    InsightIA.periodo_inicio == desde,
                    InsightIA.periodo_fin == hasta,
                )
            )
            for i in respuesta.insights:
                session.add(
                    InsightIA(
                        usuario_id=usuario_id,
                        tipo=i.tipo,
                        severidad=i.severidad,
                        titulo=i.titulo,
                        periodo_inicio=desde,
                        periodo_fin=hasta,
                        payload={
                            "detalle": i.detalle,
                            "categoria": i.categoria,
                            "metrica": i.metrica,
                            "delta_pct": i.delta_pct,
                        },
                        modelo=modelo,
                        tokens_usados=tokens,
                    )
                )

        return f"usuario {usuario_id}: {len(respuesta.insights)} insights, {tokens} tokens"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Genera insights financieros con Qwen")
    parser.add_argument("--usuario", type=int, help="Solo este usuario_id")
    parser.add_argument(
        "--seco", action="store_true", help="Muestra el prompt y no llama al modelo"
    )
    args = parser.parse_args()

    hoy = hoy_lima()
    print(f"[insights] {datetime.now(LIMA):%Y-%m-%d %H:%M} Lima")

    async with async_session() as session:
        usuarios = await usuarios_objetivo(session, args.usuario)

    if not usuarios:
        print("[insights] no hay usuarios vinculados al panel")
        return 0

    fallos = 0
    for uid in usuarios:
        try:
            print(f"[insights] {await procesar(uid, hoy, args.seco)}")
        except Exception as e:  # un usuario que falla no debe frenar a los demás
            fallos += 1
            print(f"[insights] usuario {uid}: ERROR {type(e).__name__}: {e}")

    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
