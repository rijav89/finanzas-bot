# config.py — FinanzasBot v3.0
import os
from dotenv import load_dotenv
 
load_dotenv()  # Carga el archivo .env en local
 
TOKEN         = os.environ['TOKEN']
DB_CONFIG     = os.environ['DB_CONFIG']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
