"""Contrato de lo que el modelo puede devolver.

Es estricto a propósito: cualquier campo de más o un tipo raro invalida la respuesta
completa y se reintenta. Un insight es texto que el usuario va a leer como si fuera
un hecho sobre su plata, así que es preferible no mostrar nada a mostrar algo torcido.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoInsight = Literal["patron_gasto", "alerta_presupuesto", "tendencia", "recomendacion"]
Severidad = Literal["info", "atencion", "critico"]

MAX_INSIGHTS = 5


class InsightGenerado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoInsight
    severidad: Severidad
    titulo: str = Field(min_length=3, max_length=90)
    detalle: str = Field(min_length=10, max_length=320)
    categoria: str | None = Field(default=None, max_length=40)
    #: Cifra que sostiene el insight, ya formateada (ej. "S/ 450.00")
    metrica: str | None = Field(default=None, max_length=40)
    #: Variación contra el promedio de meses previos, en porcentaje
    delta_pct: float | None = Field(default=None, ge=-1000, le=10000)


class RespuestaInsights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insights: list[InsightGenerado] = Field(max_length=MAX_INSIGHTS)


class MarcarLeido(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leido: bool = True
