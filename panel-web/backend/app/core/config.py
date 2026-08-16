from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # BD runtime (rol panel_web tras la migración 004; antes, rol postgres temporal)
    database_url: str
    # BD para migraciones Alembic (rol postgres, DDL) — no se usa en runtime
    alembic_database_url: str = ""

    # Supabase Auth (GoTrue)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    # IA
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model_text: str = "qwen-plus"

    entorno: str = "dev"
    cookie_secure: bool = True
    # Se enciende junto con la migración 004 (F6). Mientras esté apagado se evita
    # el roundtrip del SET LOCAL en cada request.
    rls_activo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
