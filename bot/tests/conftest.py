"""Hace importables los módulos de bot/ desde tests/, y evita que importar un
módulo cualquiera reviente por falta de un .env real (este equipo no tiene uno:
está en .gitignore). Los valores son placeholders — ningún test de este arnés
hace una llamada de red real."""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("DB_CONFIG", "dbname=test")
os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")
