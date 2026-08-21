# config.py — FinanzasBot v3.0
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN              = os.environ['TOKEN']
DB_CONFIG          = os.environ['DB_CONFIG']
GEMINI_API_KEY     = os.environ.get('GEMINI_API_KEY', '')   # se mantiene por si hay rollback
DASHSCOPE_API_KEY  = os.environ['DASHSCOPE_API_KEY']
QWEN_BASE_URL      = os.environ.get('QWEN_BASE_URL', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
QWEN_MODEL_TEXT    = 'qwen-plus'
QWEN_MODEL_OCR     = 'qwen-vl-plus'
QWEN_MODEL_ASR     = 'qwen3-asr-flash'
