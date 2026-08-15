"""Envelope estándar de la API: {"data": ..., "error": null}."""
from typing import Any


def ok(data: Any) -> dict:
    return {"data": data, "error": None}


def err(codigo: str) -> dict:
    return {"data": None, "error": codigo}
