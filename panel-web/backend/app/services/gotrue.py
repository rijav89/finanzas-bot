"""Cliente mínimo de Supabase Auth (GoTrue). El backend es proxy: el navegador nunca ve tokens."""
import httpx
from fastapi import HTTPException

from app.core.config import get_settings


class GoTrueClient:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    @classmethod
    def desde_settings(cls) -> "GoTrueClient":
        s = get_settings()
        return cls(
            httpx.AsyncClient(
                base_url=f"{s.supabase_url}/auth/v1",
                headers={"apikey": s.supabase_anon_key},
                timeout=10.0,
            )
        )

    async def login(self, email: str, password: str) -> dict:
        r = await self._client.post(
            "/token", params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="credenciales_invalidas")
        return r.json()

    async def signup(self, email: str, password: str) -> dict:
        """Alta por la vía pública, con la clave anónima.

        No se usa la API de administración a propósito: exigiría guardar la
        service_role key —que puede todo sobre el proyecto— en el servidor del panel.
        Quien decide si alguien puede registrarse es el código del bot, no Supabase.

        Con la confirmación por correo desactivada, la respuesta ya trae la sesión.
        """
        r = await self._client.post(
            "/signup", json={"email": email, "password": password}
        )
        if r.status_code == 422 or (
            r.status_code == 400 and "already" in r.text.lower()
        ):
            raise HTTPException(status_code=409, detail="correo_ya_registrado")
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail="alta_rechazada")
        return r.json()

    async def refresh(self, refresh_token: str) -> dict:
        r = await self._client.post(
            "/token", params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="sesion_expirada")
        return r.json()

    async def logout(self, access_token: str) -> None:
        # Best-effort: aunque falle, las cookies se limpian igual
        try:
            await self._client.post(
                "/logout", headers={"Authorization": f"Bearer {access_token}"}
            )
        except httpx.HTTPError:
            pass

    async def aclose(self) -> None:
        await self._client.aclose()


_instancia: GoTrueClient | None = None


def get_gotrue() -> GoTrueClient:
    """Dependencia FastAPI; los tests la overridean con un cliente mockeado."""
    global _instancia
    if _instancia is None:
        _instancia = GoTrueClient.desde_settings()
    return _instancia
