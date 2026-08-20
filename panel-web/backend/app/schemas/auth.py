from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(_Estricto):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class VincularIn(_Estricto):
    codigo: str = Field(min_length=6, max_length=16, pattern=r"^[A-Za-z0-9]+$")


class RegistroIn(_Estricto):
    """Alta desde el panel. El código lo entrega el bot con /vincular: es la prueba
    de que la persona es dueña de esos datos de Telegram."""

    email: EmailStr
    #: Mínimo de Supabase por defecto; subirlo acá no serviría si allá es menor
    password: str = Field(min_length=8, max_length=200)
    codigo: str = Field(min_length=6, max_length=16, pattern=r"^[A-Za-z0-9]+$")
