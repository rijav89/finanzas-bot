"""Toca la base una vez al día para que Supabase no pause el proyecto.

El plan gratuito pausa proyectos sin actividad por 7 días, y despausarlo es manual
desde el dashboard: el bot deja de responder hasta que alguien entra a la web.
Un SELECT diario cuesta nada y elimina ese modo de falla.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.db.session import async_session  # noqa: E402


async def main() -> int:
    ahora = datetime.now(ZoneInfo("America/Lima"))
    try:
        async with async_session() as s:
            usuarios = await s.scalar(text("SELECT COUNT(*) FROM usuarios"))
        print(f"[keepalive] {ahora:%Y-%m-%d %H:%M} Lima · ok · {usuarios} usuarios")
        return 0
    except Exception as e:
        print(f"[keepalive] {ahora:%Y-%m-%d %H:%M} Lima · ERROR {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
