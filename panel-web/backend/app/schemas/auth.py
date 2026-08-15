from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginIn(_Estricto):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class VincularIn(_Estricto):
    codigo: str = Field(min_length=6, max_length=16, pattern=r"^[A-Za-z0-9]+$")
