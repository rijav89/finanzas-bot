# Entrada multimodal del bot: implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El bot registra gastos a partir de notas de voz, vouchers de depósito
bancario y capturas de historial con varios movimientos, preguntando por lo que
falte (medio de pago, categoría) en vez de asumirlo.

**Architecture:** La voz se transcribe y entra al pipeline de texto que ya existe
(`extraer_gastos`). El OCR de imágenes pasa de devolver un voucher a devolver una
lista de movimientos: uno solo sigue el camino actual, varios entran a un flujo
nuevo de checklist con deduplicación por monto+fecha. Una cola de preguntas en
memoria (mismo patrón que `datos_pendientes` hoy) cubre medio y categoría faltantes
en los tres caminos de entrada.

**Tech Stack:** Python 3.12, `python-telegram-bot` 21.9, `openai` (cliente
OpenAI-compatible contra Qwen/DashScope), `psycopg` + `psycopg_pool`, `pytest` (nuevo,
solo para las funciones puras de este plan).

**Spec:** `docs/superpowers/specs/2026-08-20-entrada-multimodal-design.md`

## Global Constraints

- Sin dependencias de sistema nuevas: nada de `ffmpeg`/`pydub` — el endpoint de Qwen
  acepta el OGG/Opus de Telegram tal cual (verificado en producción).
- El estado de flujos a medias vive en memoria del proceso (dicts por
  `telegram_id`), igual que `datos_pendientes`/`ingreso_pendiente` hoy. No se
  persiste en la base.
- v1 solo importa **gastos** desde una captura de historial. Los ingresos que
  aparezcan en esa misma imagen no se registran; el mensaje final lo dice
  explícito.
- No se corrige automáticamente un año ambiguo en una fecha leída por OCR: se usa
  el año actual y el usuario corrige a mano si hace falta.
- La deduplicación de un lote importado es solo por (monto ±0.01, fecha exacta)
  contra `transacciones` e `ingresos` — no por texto/destinatario.
- Seguir el estilo existente de `bot.py`: mensajes con emoji + Markdown, manejo de
  errores con `try/except Exception` y un mensaje al usuario, nunca una excepción
  sin capturar hacia el handler de Telegram.
- Sin test harness de Telegram en este repo: las funciones puras (extracción,
  deduplicación) llevan tests de `pytest` reales; los flujos interactivos
  (checklist, preguntas por botón) se verifican a mano contra el bot de pruebas,
  como ya se hace hoy para el resto del bot.

---

## Task 1: Transcripción de audio

**Files:**
- Modify: `bot/config.py`
- Create: `bot/audio.py`

**Interfaces:**
- Produces: `audio.transcribir_audio(file_path: str) -> str | None` — texto
  transcripto, o `None` si el audio no se pudo transcribir (falla de red, JSON
  vacío, etc.). Tareas posteriores (Task 4) llaman a esta función.

- [ ] **Step 1: Agregar el modelo de ASR a la configuración**

Modifica `bot/config.py`. El archivo completo hoy es:

```python
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
```

Agregá una línea al final:

```python
QWEN_MODEL_ASR     = 'qwen3-asr-flash'
```

No hace falta ninguna variable de entorno nueva: usa la misma `DASHSCOPE_API_KEY` y
`QWEN_BASE_URL` que ya existen.

- [ ] **Step 2: Crear `bot/audio.py`**

```python
"""
audio.py — FinanzasBot v3.1
Transcribe notas de voz de Telegram (OGG/Opus) con Qwen ASR.
"""

import base64
import pathlib

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_ASR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)


def transcribir_audio(file_path: str) -> str | None:
    """OGG/Opus de Telegram -> texto. None si no se pudo transcribir.

    Telegram siempre manda notas de voz en OGG/Opus, así que el formato va fijo
    (no hace falta detectar la extensión como en ocr.py).
    """
    audio_bytes = pathlib.Path(file_path).read_bytes()
    b64 = base64.b64encode(audio_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_ASR,
            messages=[
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "El audio está en español."}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/ogg;base64,{b64}",
                                "format": "ogg",
                            },
                        },
                    ],
                },
            ],
        )
        texto = response.choices[0].message.content
        return texto.strip() if isinstance(texto, str) and texto.strip() else None
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")
        return None
```

- [ ] **Step 3: Verificación manual contra la API real**

No hay forma de probar transcripción de voz con un test automatizado (depende de
la red y de la cuota de Qwen), así que se verifica una vez con un script manual,
igual que se hizo para validar el endpoint antes de aprobar el diseño.

Desde el servidor del bot (o localmente con las variables de entorno del `.env`
cargadas), corré:

```bash
cd /home/ubuntu/finanzas-bot/bot
python3 -c "
from audio import transcribir_audio
# Grabá una nota de voz corta con Telegram, descargala a mano una vez, o usá
# cualquier archivo .ogg de prueba con voz en español.
print(transcribir_audio('/tmp/prueba.ogg'))
"
```

Esperado: imprime el texto transcripto, no `None` ni una traza de error.

- [ ] **Step 4: Commit**

```bash
git add bot/config.py bot/audio.py
git commit -m "Transcripcion de notas de voz con qwen3-asr-flash"
```

---

## Task 2: Arnés de pruebas + `medio` opcional en la extracción de gastos

Hoy `bot/` no tiene ningún test automatizado. Este task monta lo mínimo necesario
(`pytest` + un `conftest.py` que no depende de un `.env` real) y lo usa para la
primera pieza genuinamente testeable: que `extraer_gastos` reconozca cuando el
usuario ya dijo cómo pagó (texto o, más adelante, voz transcripta a texto).

**Files:**
- Create: `bot/requirements-dev.txt`
- Create: `bot/tests/conftest.py`
- Create: `bot/tests/test_gastos_manual.py`
- Modify: `bot/gastos_manual.py`

**Interfaces:**
- Produces: `gastos_manual.MEDIOS_DISPONIBLES: list[str]`, y `extraer_gastos` ahora
  incluye una clave `"medio"` (`str | None`) en cada dict de gasto que devuelve.
  Task 3 consume esta clave para decidir si hace falta preguntar.

- [ ] **Step 1: Crear `bot/requirements-dev.txt`**

```
pytest
```

Separado de `requirements.txt` a propósito: el servidor de producción no necesita
`pytest` instalado, y es una máquina de 1GB de RAM donde cada paquete de más
cuenta.

- [ ] **Step 2: Crear `bot/tests/conftest.py`**

```python
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
```

- [ ] **Step 3: Escribir el test que falla**

Crear `bot/tests/test_gastos_manual.py`:

```python
from gastos_manual import MEDIOS_DISPONIBLES, _validar


def test_medio_reconocido_se_normaliza():
    assert _validar("yape", MEDIOS_DISPONIBLES, None) == "Yape"


def test_medio_no_mencionado_devuelve_none():
    assert _validar(None, MEDIOS_DISPONIBLES, None) is None


def test_medio_invalido_devuelve_none():
    assert _validar("bitcoin", MEDIOS_DISPONIBLES, None) is None


def test_medio_con_mayusculas_distintas_se_normaliza():
    assert _validar("TARJETA", MEDIOS_DISPONIBLES, None) == "Tarjeta"
```

- [ ] **Step 4: Correr los tests y confirmar que fallan**

```bash
cd bot
pip install -r requirements-dev.txt
python -m pytest tests/test_gastos_manual.py -v
```

Esperado: `ImportError: cannot import name 'MEDIOS_DISPONIBLES' from 'gastos_manual'`
— la constante todavía no existe.

- [ ] **Step 5: Agregar `MEDIOS_DISPONIBLES` y extender `PROMPT_GASTOS`**

En `bot/gastos_manual.py`, el bloque actual (líneas ~53-65) es:

```python
# --- 2. Ingreso ---
PROMPT_INGRESO = """Hoy es {hoy}.
```

Justo **antes** de ese bloque, agregá:

```python
# Mismas opciones que ya usan los botones de "¿con qué medio pagaste?" en
# _procesar_y_guardar_gastos — si se agrega un medio acá hay que agregarlo ahí.
MEDIOS_DISPONIBLES = ["Yape", "Plin", "Efectivo", "Tarjeta", "Transferencia"]


# --- 2. Ingreso ---
PROMPT_INGRESO = """Hoy es {hoy}.
```

Ahora buscá el bloque `PROMPT_GASTOS` (más abajo en el mismo archivo):

```python
# --- 3. Gastos ---
PROMPT_GASTOS = """Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae fecha y lista de gastos. Responde SOLO con JSON válido:
{{
  "fecha": "<YYYY-MM-DD>",
  "gastos": [
    {{
      "monto": <float>,
      "descripcion": "<descripción>",
      "categoria": "<{categorias}>",
      "cuenta_origen": "<nombre de cuenta o Principal>"
    }}
  ]
}}
Adapta 'fecha' según mencione el usuario (ej. "ayer" resta 1 día). Si no menciona, usa {hoy}."""
```

Reemplazalo por:

```python
# --- 3. Gastos ---
PROMPT_GASTOS = """Hoy es {hoy}.
Cuentas disponibles: {cuentas}
Usuario: "{mensaje}"
Extrae fecha y lista de gastos. Responde SOLO con JSON válido:
{{
  "fecha": "<YYYY-MM-DD>",
  "gastos": [
    {{
      "monto": <float>,
      "descripcion": "<descripción>",
      "categoria": "<{categorias}>",
      "medio": "<{medios} o null si el usuario no lo menciona>",
      "cuenta_origen": "<nombre de cuenta o Principal>"
    }}
  ]
}}
Adapta 'fecha' según mencione el usuario (ej. "ayer" resta 1 día). Si no menciona, usa {hoy}.
'medio' es null salvo que el usuario diga explícitamente cómo pagó (ej. "con yape", "en efectivo")."""
```

- [ ] **Step 6: Extender `extraer_gastos` para pasar y validar `medio`**

En el mismo archivo, buscá:

```python
def extraer_gastos(mensaje: str, cuentas=None, usuario_id=None) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    opciones = _opciones("gasto", usuario_id)
    try:
        raw = _call(PROMPT_GASTOS.format(
            mensaje=mensaje, hoy=hoy, cuentas=cuentas_str, categorias="|".join(opciones),
        ))
        data = json.loads(raw)
        gastos = data.get("gastos", [])
        for g in gastos:
            g["categoria"] = _validar(g.get("categoria"), opciones, "Otros")
        return gastos, data.get("fecha", hoy)
    except Exception:
        return [], hoy
```

Reemplazalo por:

```python
def extraer_gastos(mensaje: str, cuentas=None, usuario_id=None) -> tuple[list[dict], str]:
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    cuentas_str = ", ".join(cuentas) if cuentas else "Principal"
    opciones = _opciones("gasto", usuario_id)
    try:
        raw = _call(PROMPT_GASTOS.format(
            mensaje=mensaje, hoy=hoy, cuentas=cuentas_str, categorias="|".join(opciones),
            medios="|".join(MEDIOS_DISPONIBLES),
        ))
        data = json.loads(raw)
        gastos = data.get("gastos", [])
        for g in gastos:
            g["categoria"] = _validar(g.get("categoria"), opciones, "Otros")
            g["medio"] = _validar(g.get("medio"), MEDIOS_DISPONIBLES, None)
        return gastos, data.get("fecha", hoy)
    except Exception:
        return [], hoy
```

- [ ] **Step 7: Correr los tests y confirmar que pasan**

```bash
python -m pytest tests/test_gastos_manual.py -v
```

Esperado: los 4 tests en verde.

- [ ] **Step 8: Verificación manual de la extracción completa**

```bash
python3 -c "
from gastos_manual import extraer_gastos
gastos, fecha = extraer_gastos('ayer gasté 20 en comida y 10 en ropa, pagué con yape')
for g in gastos:
    print(g)
print('fecha:', fecha)
"
```

Esperado: los dos gastos con `"medio": "Yape"`.

```bash
python3 -c "
from gastos_manual import extraer_gastos
gastos, fecha = extraer_gastos('ayer gasté 30 en bebidas')
for g in gastos:
    print(g)
"
```

Esperado: el gasto con `"medio": None`.

- [ ] **Step 9: Commit**

```bash
git add bot/requirements-dev.txt bot/tests/ bot/gastos_manual.py
git commit -m "Extrae el medio de pago del texto cuando el usuario lo menciona

Arranca el arnes de pytest para bot/, que hoy no tenia ninguno."
```

---

## Task 3: Guardar y preguntar solo lo que falta (medio y categoría)

Esta es la pieza central: cambia `_procesar_y_guardar_gastos` para que use el
`medio` que ya viene de Task 2 (guardando "Manual" si no vino ninguno), y agrega
una cola de preguntas de categoría para los gastos que el clasificador no supo
ubicar. Los botones de medio ya existen (`medio_...` en `handle_callback`); acá
se vuelven condicionales en vez de aparecer siempre.

**Files:**
- Modify: `bot/db.py`
- Modify: `bot/bot.py`

**Interfaces:**
- Consumes: `extraer_gastos(...)` de Task 2 (cada gasto trae `"medio"`).
  `catalogo("gasto", usuario_id)` de `categorias.py` (ya existe).
- Produces: `guardar_transaccion(...) -> int` (ahora devuelve el id insertado).
  `bot.py::categoria_pendiente_cola: dict[int, list[dict]]`,
  `bot.py::encolar_pregunta_categoria(telegram_id, trans_id, monto, descripcion)`,
  `bot.py::preguntar_siguiente_categoria(context, chat_id, telegram_id)`,
  `bot.py::teclado_medio_gasto() -> InlineKeyboardMarkup`. Task 4 llama a
  `_procesar_y_guardar_gastos` con la nueva firma
  `(update, context, usuario_id, mensaje)`. Task 8 llama a
  `encolar_pregunta_categoria` y `preguntar_siguiente_categoria` desde el flujo de
  importación por lotes.

- [ ] **Step 1: `guardar_transaccion` devuelve el id insertado**

En `bot/db.py`, buscá:

```python
def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario="No detectado", fecha_voucher="No detectada", fecha=None, cuenta_id=None):
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if cuenta_id is None:
                cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
                res = cur.fetchone()
                cuenta_id = res[0] if res else None

            if fecha:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id),
                )
            conn.commit()
```

Reemplazalo por:

```python
def guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario="No detectado", fecha_voucher="No detectada", fecha=None, cuenta_id=None) -> int:
    """Devuelve el id de la transacción insertada."""
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            if cuenta_id is None:
                cur.execute("SELECT id FROM cuentas WHERE usuario_id=%s AND es_principal=TRUE", (usuario_id,))
                res = cur.fetchone()
                cuenta_id = res[0] if res else None

            if fecha:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, fecha, cuenta_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO transacciones
                        (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (usuario_id, monto, medio, descripcion, categoria, destinatario, fecha_voucher, cuenta_id),
                )
            transaccion_id = cur.fetchone()[0]
            conn.commit()
            return transaccion_id
```

Los dos call sites existentes (`registrar_transaccion` y
`_procesar_y_guardar_gastos`) ignoran hoy el valor de retorno — `None` implícito
antes, un `int` ahora — así que este cambio no rompe nada por sí solo.

- [ ] **Step 2: Importar `catalogo` en `bot.py`**

En `bot/bot.py`, buscá la línea:

```python
from categorias import clasificar_gasto, clasificar_ingreso
```

Reemplazala por:

```python
from categorias import clasificar_gasto, clasificar_ingreso, catalogo
```

- [ ] **Step 3: Agregar el estado de la cola de categorías**

Buscá el bloque de dicts de estado en memoria:

```python
datos_pendientes         = {}
registro_manual_pendiente = {}
ingreso_pendiente        = {}
pago_fijo_pendiente      = {}
edicion_pendiente        = {}
transferencia_pendiente  = {}
cuenta_pendiente         = {}
```

Agregá una línea:

```python
datos_pendientes         = {}
registro_manual_pendiente = {}
ingreso_pendiente        = {}
pago_fijo_pendiente      = {}
edicion_pendiente        = {}
transferencia_pendiente  = {}
cuenta_pendiente         = {}
categoria_pendiente_cola = {}  # telegram_id -> [{"id", "monto", "descripcion"}, ...]
```

- [ ] **Step 4: Agregar los helpers de la cola de categorías**

Justo antes de la definición de `_procesar_y_guardar_gastos` (buscá
`async def _procesar_y_guardar_gastos(update, usuario_id, mensaje):`), agregá:

```python
def teclado_medio_gasto() -> InlineKeyboardMarkup:
    """Mismo teclado que ya usan los gastos de texto — factorizado para
    reusarlo también desde la importación por lotes (Task 8)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 Yape", callback_data="medio_Yape"),
            InlineKeyboardButton("💙 Plin", callback_data="medio_Plin"),
        ],
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="medio_Efectivo"),
            InlineKeyboardButton("💳 Tarjeta", callback_data="medio_Tarjeta"),
        ],
        [
            InlineKeyboardButton("🏦 Transferencia", callback_data="medio_Transferencia"),
            InlineKeyboardButton("⏭️ Omitir", callback_data="medio_Manual"),
        ],
    ])


def encolar_pregunta_categoria(telegram_id: int, trans_id: int, monto: float, descripcion: str) -> None:
    """El clasificador automático no supo ubicar este gasto (cayó en 'Otros'):
    se pregunta después, sin bloquear el guardado."""
    categoria_pendiente_cola.setdefault(telegram_id, []).append({
        "id": trans_id, "monto": float(monto), "descripcion": descripcion,
    })


async def preguntar_siguiente_categoria(context: ContextTypes.DEFAULT_TYPE, chat_id: int, telegram_id: int) -> None:
    """Muestra la pregunta del primer gasto en cola, sin sacarlo todavía —
    se saca cuando el usuario responde (ver handle_callback, 'catq_')."""
    cola = categoria_pendiente_cola.get(telegram_id) or []
    if not cola:
        return

    item = cola[0]
    usuario_id = obtener_o_crear_usuario(telegram_id)
    opciones = list(catalogo("gasto", usuario_id).keys())

    filas = [
        [InlineKeyboardButton(c, callback_data=f"catq_{c}") for c in opciones[i:i + 3]]
        for i in range(0, len(opciones), 3)
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "¿En qué categoría entra este gasto?\n\n"
            f"💰 S/ {item['monto']:.2f} — {item['descripcion']}"
        ),
        reply_markup=InlineKeyboardMarkup(filas),
    )
```

- [ ] **Step 5: Reescribir `_procesar_y_guardar_gastos`**

Buscá la función completa:

```python
async def _procesar_y_guardar_gastos(update, usuario_id, mensaje):
    """Extrae gastos del mensaje, detecta fecha, pregunta medio y guarda."""
    from datetime import datetime
    cuentas = obtener_cuentas(usuario_id)
    nombres_cuentas = [c[1] for c in cuentas]
    
    await update.message.reply_text("⏳ Analizando tus gastos...")
    gastos, fecha_str = extraer_gastos(mensaje, nombres_cuentas, usuario_id)

    if not gastos:
        await update.message.reply_text(
            "⚠️ No pude identificar gastos en tu mensaje.\n"
            "Intenta ser más específico:\n"
            "_\"Gasté 50 soles en almuerzo y 20 en taxi\"_",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        return

    # Convertir fecha_str a datetime
    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
    except Exception:
        fecha_dt = None

    hoy = datetime.now().strftime("%Y-%m-%d")
    es_fecha_distinta = fecha_str and fecha_str != hoy

    resumen_texto = "✅ *Gastos registrados:*\n\n"
    total = 0
    for gasto in gastos:
        monto = gasto.get("monto", 0)
        descripcion = gasto.get("descripcion", "Sin descripción")
        categoria = gasto.get("categoria", "Otros")
        cuenta_origen_str = gasto.get("cuenta_origen", "Principal")
        cuenta_origen_id = obtener_cuenta_por_nombre(usuario_id, cuenta_origen_str) or obtener_cuenta_principal(usuario_id)
        
        emoji = EMOJIS_CATEGORIA.get(categoria, "📦")
        guardar_transaccion(
            usuario_id, monto=monto, medio="Manual",
            descripcion=descripcion, categoria=categoria,
            destinatario="—", fecha_voucher="—",
            fecha=fecha_dt, cuenta_id=cuenta_origen_id
        )
        resumen_texto += f"{emoji} S/ {monto:.2f} — {descripcion} _{categoria}_\n"
        total += float(monto)

    resumen_texto += f"\n💰 *Total registrado: S/ {total:.2f}*"
    if es_fecha_distinta:
        fecha_legible = fecha_dt.strftime("%d/%m/%Y") if fecha_dt else fecha_str
        resumen_texto += f"\n📅 Fecha registrada: *{fecha_legible}*"

    teclado_medio = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱 Yape", callback_data="medio_Yape"),
            InlineKeyboardButton("💙 Plin", callback_data="medio_Plin"),
        ],
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="medio_Efectivo"),
            InlineKeyboardButton("💳 Tarjeta", callback_data="medio_Tarjeta"),
        ],
        [
            InlineKeyboardButton("🏦 Transferencia", callback_data="medio_Transferencia"),
            InlineKeyboardButton("⏭️ Omitir", callback_data="medio_Manual"),
        ],
    ])

    await update.message.reply_text(
        resumen_texto + "\n\n¿Con qué medio pagaste?",
        parse_mode="Markdown",
        reply_markup=teclado_medio
    )
```

Reemplazala por:

```python
async def _procesar_y_guardar_gastos(update, context, usuario_id, mensaje):
    """Extrae gastos del mensaje, guarda, y pregunta solo lo que falte."""
    from datetime import datetime
    cuentas = obtener_cuentas(usuario_id)
    nombres_cuentas = [c[1] for c in cuentas]

    await update.message.reply_text("⏳ Analizando tus gastos...")
    gastos, fecha_str = extraer_gastos(mensaje, nombres_cuentas, usuario_id)

    if not gastos:
        await update.message.reply_text(
            "⚠️ No pude identificar gastos en tu mensaje.\n"
            "Intenta ser más específico:\n"
            "_\"Gasté 50 soles en almuerzo y 20 en taxi\"_",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        return

    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
    except Exception:
        fecha_dt = None

    hoy = datetime.now().strftime("%Y-%m-%d")
    es_fecha_distinta = fecha_str and fecha_str != hoy
    telegram_id = update.message.from_user.id

    resumen_texto = "✅ *Gastos registrados:*\n\n"
    total = 0
    falta_medio = False
    for gasto in gastos:
        monto = gasto.get("monto", 0)
        descripcion = gasto.get("descripcion", "Sin descripción")
        categoria = gasto.get("categoria", "Otros")
        medio = gasto.get("medio") or "Manual"
        if medio == "Manual":
            falta_medio = True
        cuenta_origen_str = gasto.get("cuenta_origen", "Principal")
        cuenta_origen_id = obtener_cuenta_por_nombre(usuario_id, cuenta_origen_str) or obtener_cuenta_principal(usuario_id)

        emoji = EMOJIS_CATEGORIA.get(categoria, "📦")
        trans_id = guardar_transaccion(
            usuario_id, monto=monto, medio=medio,
            descripcion=descripcion, categoria=categoria,
            destinatario="—", fecha_voucher="—",
            fecha=fecha_dt, cuenta_id=cuenta_origen_id
        )
        if categoria == "Otros":
            encolar_pregunta_categoria(telegram_id, trans_id, monto, descripcion)
        resumen_texto += f"{emoji} S/ {monto:.2f} — {descripcion} _{categoria}_\n"
        total += float(monto)

    resumen_texto += f"\n💰 *Total registrado: S/ {total:.2f}*"
    if es_fecha_distinta:
        fecha_legible = fecha_dt.strftime("%d/%m/%Y") if fecha_dt else fecha_str
        resumen_texto += f"\n📅 Fecha registrada: *{fecha_legible}*"

    await update.message.reply_text(resumen_texto, parse_mode="Markdown")

    # Medio y categoría son preguntas independientes: si faltan las dos, se
    # mandan las dos — el usuario responde en el orden que quiera.
    if falta_medio:
        await update.message.reply_text(
            "¿Con qué medio pagaste los que no especificaste?",
            reply_markup=teclado_medio_gasto(),
        )
    if categoria_pendiente_cola.get(telegram_id):
        await preguntar_siguiente_categoria(context, update.effective_chat.id, telegram_id)
```

- [ ] **Step 6: Actualizar los dos call sites existentes**

Buscá (dentro de `handle_texto`):

```python
    elif intencion == "REGISTRAR_GASTOS":
        await _procesar_y_guardar_gastos(update, usuario_id, mensaje)
```

Reemplazá por:

```python
    elif intencion == "REGISTRAR_GASTOS":
        await _procesar_y_guardar_gastos(update, context, usuario_id, mensaje)
```

Buscá (dentro de `handle_descripcion_manual`):

```python
    del registro_manual_pendiente[telegram_id]
    usuario_id = obtener_o_crear_usuario(telegram_id)
    await _procesar_y_guardar_gastos(update, usuario_id, mensaje)
```

Reemplazá por:

```python
    del registro_manual_pendiente[telegram_id]
    usuario_id = obtener_o_crear_usuario(telegram_id)
    await _procesar_y_guardar_gastos(update, context, usuario_id, mensaje)
```

- [ ] **Step 7: Agregar el callback de respuesta a la pregunta de categoría**

En `handle_callback`, buscá el bloque:

```python
    # ── Selección de medio de pago (gastos) ───────────────────────────
    elif accion.startswith("medio_"):
        medio = accion.replace("medio_", "")
        actualizar_medio_ultimas(usuario_id, medio)
        await safe_edit(query,
            query.message.text.replace("\n\n¿Con qué medio pagaste?", f"\n\n📱 Medio: *{medio}*"),
            parse_mode="Markdown", reply_markup=menu_principal()
        )
```

Justo después de ese bloque (antes de `# ── Eliminar transacción`), agregá:

```python
    # ── Respuesta a la cola de preguntas de categoría ──────────────────
    elif accion.startswith("catq_"):
        categoria_elegida = accion[len("catq_"):]
        telegram_id_cb = query.from_user.id
        cola = categoria_pendiente_cola.get(telegram_id_cb) or []
        if not cola:
            await safe_edit(query, "Esa pregunta ya no está activa.", reply_markup=menu_principal())
        else:
            item = cola.pop(0)
            editar_transaccion(item["id"], usuario_id, item["monto"], item["descripcion"], categoria_elegida)
            await safe_edit(
                query,
                f"✅ Categoría actualizada: *{categoria_elegida}*\n"
                f"💰 S/ {item['monto']:.2f} — {item['descripcion']}",
                parse_mode="Markdown",
            )
            if cola:
                await preguntar_siguiente_categoria(context, query.message.chat_id, telegram_id_cb)
```

Nota: `accion.startswith("medio_")` también matchea `medio_Manual` con el "⏭️
Omitir" — eso ya es el comportamiento existente, sin cambios acá.

- [ ] **Step 8: Verificación manual**

Desde Telegram, con el bot desplegado:

1. Escribí `"gasté 30 en bebidas"` (sin medio). Esperado: se registra, y aparece
   el teclado "¿Con qué medio pagaste los que no especificaste?".
2. Escribí `"gasté 30 en bebidas, pagué con yape"`. Esperado: se registra
   directo, **sin** que aparezca el teclado de medio.
3. Escribí algo ambiguo que el clasificador no pueda ubicar (ej. `"gasté 15 en
   una vaina rara"`). Esperado: se registra en "Otros" y aparece la pregunta de
   categoría con botones.

- [ ] **Step 9: Commit**

```bash
git add bot/db.py bot/bot.py
git commit -m "Pregunta el medio de pago y la categoria solo cuando faltan"
```

---

## Task 4: Nota de voz conectada al pipeline de texto

**Files:**
- Modify: `bot/bot.py`

**Interfaces:**
- Consumes: `audio.transcribir_audio` (Task 1), `_procesar_y_guardar_gastos`
  (Task 3, firma `(update, context, usuario_id, mensaje)`).

- [ ] **Step 1: Importar `transcribir_audio`**

En `bot/bot.py`, buscá:

```python
from ocr import procesar_voucher
```

Reemplazá por:

```python
from ocr import procesar_voucher
from audio import transcribir_audio
```

- [ ] **Step 2: Agregar `handle_voice`**

Justo antes de `# ── Procesar imagen ─────` (donde empieza `handle_photo`),
agregá:

```python
# ── Procesar nota de voz ─────────────────────────────────────────────────

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe la nota de voz y la manda por el mismo camino que un gasto
    escrito. Por ahora solo gastos — de "recibí 200" por voz no hay ejemplo
    pedido, y ampliarlo es agregar un elif más adelante, no un flujo nuevo."""
    voice = update.message.voice
    if voice.duration > 120:
        await update.message.reply_text(
            "⚠️ La nota es muy larga (máximo 2 minutos). Grábala más corta o escribe el gasto.",
            reply_markup=menu_principal()
        )
        return

    file = await voice.get_file()
    file_path = f"temp_voice_{update.message.message_id}.ogg"
    await file.download_to_drive(file_path)

    try:
        await update.message.reply_text("🎙️ Escuchando...")
        texto = transcribir_audio(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    if not texto:
        await update.message.reply_text(
            "⚠️ No pude entender el audio. Intenta de nuevo o escribe el gasto.",
            reply_markup=menu_principal()
        )
        return

    await update.message.reply_text(f"🗣️ Te escuché decir:\n_\"{texto}\"_", parse_mode="Markdown")

    telegram_id = update.message.from_user.id
    usuario_id = obtener_o_crear_usuario(telegram_id)
    intencion = detectar_intencion(texto)

    if intencion == "REGISTRAR_GASTOS":
        await _procesar_y_guardar_gastos(update, context, usuario_id, texto)
    else:
        await update.message.reply_text(
            "Por ahora las notas de voz solo registran gastos. "
            "Para otras acciones, escríbeme o usa el menú.",
            reply_markup=menu_principal()
        )
```

- [ ] **Step 3: Registrar el handler en `main()`**

Buscá:

```python
    app.add_handler(conv_nueva_cuenta)
    app.add_handler(CallbackQueryHandler(handle_callback))
```

Reemplazá por:

```python
    app.add_handler(conv_nueva_cuenta)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_callback))
```

- [ ] **Step 4: Verificación manual**

Desde Telegram, mandá una nota de voz diciendo exactamente:
*"ayer me gasté 20 soles en comida, 10 en ropa, los pagué con yape"*.

Esperado:
1. Aparece "🎙️ Escuchando...".
2. Aparece la transcripción entre comillas.
3. Se registran los dos gastos con fecha de ayer y medio Yape, **sin** que
   aparezca el teclado de medio (ya vino en el audio).

Mandá una segunda nota diciendo *"ayer gasté 30 en bebidas"* (sin medio).
Esperado: se registra y aparece el teclado de medio.

- [ ] **Step 5: Commit**

```bash
git add bot/bot.py
git commit -m "Notas de voz: transcribir y registrar como un gasto de texto"
```

---

## Task 5: OCR devuelve una lista de movimientos, no un voucher único

Este task solo cambia `ocr.py`. No toca `bot.py` todavía — eso es el Task 6, para
poder probar la extracción de forma aislada primero.

**Files:**
- Modify: `bot/ocr.py`

**Interfaces:**
- Produces: `ocr.procesar_voucher(file_path: str) -> list[dict]`. Cada dict:
  `{"monto": str, "medio": str, "destinatario": str, "descripcion": str, "fecha": str}`.
  Un voucher simple es una lista de longitud 1; una captura de historial, de
  longitud N. `"monto"` sigue siendo `"No detectado"` como string cuando no se
  pudo leer (mismo contrato que antes, para no romper el chequeo que ya hace
  `handle_photo`). Task 6 consume esta lista.

- [ ] **Step 1: Reescribir `ocr.py`**

El archivo completo hoy es:

```python
"""
ocr.py — FinanzasBot v3.1
Usa Qwen VL OCR (Alibaba Cloud) con OpenAI-compatible API.
"""

import json
import base64
import pathlib
from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_OCR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

PROMPT = """Analiza esta imagen de un voucher de pago (Yape o Plin de Peru).
Extrae los datos y responde SOLO con un JSON válido, sin markdown ni explicaciones.

Formato exacto:
{
  "monto": "85.50",
  "medio": "Yape",
  "destinatario": "Juan Perez",
  "fecha": "2026-03-19"
}

Reglas:
- monto: solo el número, sin S/. Si no se detecta usa "No detectado"
- medio: "Yape", "Plin" o "No identificado"
- destinatario: nombre del destinatario o "No detectado"
- fecha: formato YYYY-MM-DD o "No detectada"
"""

def procesar_voucher(file_path: str) -> tuple[str, str, str, str]:
    """
    Procesa un voucher usando Qwen VL OCR y retorna monto, medio, destinatario, fecha.
    """
    image_bytes = pathlib.Path(file_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    suffix = pathlib.Path(file_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_OCR,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        monto       = data.get("monto", "No detectado")
        medio       = data.get("medio", "No identificado")
        destinatario = data.get("destinatario", "No detectado")
        fecha       = data.get("fecha", "No detectada")

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        monto       = "No detectado"
        medio       = "No identificado"
        destinatario = "No detectado"
        fecha       = "No detectada"

    return monto, medio, destinatario, fecha
```

Reemplazalo entero por:

```python
"""
ocr.py — FinanzasBot v3.1
Usa Qwen VL OCR (Alibaba Cloud) con OpenAI-compatible API.
"""

import json
import base64
import pathlib
from datetime import date

from openai import OpenAI
from config import DASHSCOPE_API_KEY, QWEN_BASE_URL, QWEN_MODEL_OCR

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=QWEN_BASE_URL,
)

PROMPT = """Analiza esta imagen financiera peruana. Puede ser:
(a) un voucher de UN SOLO pago (Yape, Plin o depósito/transferencia bancaria), o
(b) una captura de un HISTORIAL con varios movimientos listados (lista de Yape,
    estado de cuenta, historial de transacciones de una app de banco).

Responde SOLO con un array JSON, sin markdown ni explicaciones — incluso si hay
un solo movimiento, va dentro de un array de un elemento.

Formato exacto de cada elemento:
{
  "monto": "85.50",
  "medio": "Yape",
  "destinatario": "Juan Perez",
  "descripcion": "concepto visible, ej. 'Yape a Rosa' o 'Deposito'",
  "fecha": "2026-03-19"
}

Reglas:
- Si es un voucher de un solo pago, el array tiene un solo elemento.
- Si es un historial con una tabla o lista, incluí TODOS los movimientos que
  veas, uno por elemento, en el mismo orden en que aparecen en la imagen.
- Si varios movimientos comparten una fecha visible como encabezado de sección
  (ej. "Hoy", "15 de agosto"), aplicá esa fecha a cada uno de esos movimientos.
- Si el año no aparece en la imagen, usá el año actual.
- monto: solo el número, sin S/. Si no se detecta, usa "No detectado".
- medio: "Yape", "Plin", "Transferencia" o "No identificado".
- destinatario: nombre o entidad visible, o "No detectado".
- descripcion: lo que diga el concepto/glosa del movimiento, o "" si no hay nada.
- fecha: formato YYYY-MM-DD, o "No detectada" si de verdad no se puede inferir.
- No inventes datos: un campo que no se ve va con su valor por defecto.
"""


def procesar_voucher(file_path: str) -> list[dict]:
    """Lee una imagen y devuelve la lista de movimientos que encuentra.

    Un voucher de un solo pago devuelve una lista de longitud 1 — así el
    llamador no tiene que distinguir "un voucher" de "una lista de uno" como
    dos casos separados.
    """
    image_bytes = pathlib.Path(file_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    suffix = pathlib.Path(file_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    try:
        response = client.chat.completions.create(
            model=QWEN_MODEL_OCR,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        # Salvavidas: si el modelo no siguió la instrucción del array y devolvió
        # un objeto suelto (más probable con un voucher de un solo pago), se
        # envuelve igual — el llamador siempre recibe una lista.
        movimientos = data if isinstance(data, list) else [data]

        return [_normalizar(m) for m in movimientos]

    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return []


def _normalizar(m: dict) -> dict:
    fecha = m.get("fecha") or "No detectada"
    if fecha == "No detectada":
        # Sin corrección de año ambiguo (fuera de alcance): si no hay fecha
        # legible, se asume hoy y el usuario corrige a mano si hace falta.
        fecha = date.today().strftime("%Y-%m-%d")
    return {
        "monto": m.get("monto") or "No detectado",
        "medio": m.get("medio") or "No identificado",
        "destinatario": m.get("destinatario") or "No detectado",
        "descripcion": m.get("descripcion") or "",
        "fecha": fecha,
    }
```

Nota deliberada: antes, un error de red o de JSON devolvía una tupla de 4 valores
"No detectado"; ahora devuelve `[]` (lista vacía). Task 6 lo maneja igual que
antes — "no se detectó nada" es el mismo caso, solo cambia la forma de
representarlo.

- [ ] **Step 2: Script de verificación manual con imágenes reales**

No hay forma de convertir esto en un test de `pytest` — lo que puede fallar acá
es la calidad de la lectura, no lógica. Crear `bot/tests_manuales/probar_ocr.py`
(directorio nuevo, fuera de `tests/` a propósito: no lo recoge `pytest`):

```python
"""Corré esto a mano con imágenes reales antes de dar por buena la extracción.

Uso: python tests_manuales/probar_ocr.py ruta/a/la/imagen.jpg
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ocr import procesar_voucher

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python probar_ocr.py ruta/a/la/imagen.jpg")
        raise SystemExit(1)

    movimientos = procesar_voucher(sys.argv[1])
    print(f"{len(movimientos)} movimiento(s) leído(s):\n")
    for m in movimientos:
        print(json.dumps(m, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: Correr contra al menos tres imágenes reales**

Conseguí (o pedile al usuario) tres capturas: un voucher Yape/Plin, un voucher de
depósito bancario, y una captura de historial con varios movimientos. Corré:

```bash
cd bot
python3 tests_manuales/probar_ocr.py ruta/voucher_yape.jpg
python3 tests_manuales/probar_ocr.py ruta/voucher_deposito.jpg
python3 tests_manuales/probar_ocr.py ruta/historial.jpg
```

Esperado: el voucher simple devuelve una lista de 1 con montos y medio
correctos; el historial devuelve una lista de N con un elemento por fila visible
en la imagen. Si el prompt falla en algún caso, ajustalo y volvé a correr antes
de seguir — este es el paso de mayor riesgo de todo el plan (mencionado en el
spec como tal).

- [ ] **Step 4: Commit**

```bash
git add bot/ocr.py bot/tests_manuales/
git commit -m "OCR: procesar_voucher devuelve una lista de movimientos

Cubre vouchers de un solo pago (Yape/Plin/deposito) y capturas de historial
con varios movimientos, con el mismo contrato de retorno para ambos casos."
```

---

## Task 6: `handle_photo` separa voucher simple de importación por lotes

**Files:**
- Modify: `bot/bot.py`

**Interfaces:**
- Consumes: `ocr.procesar_voucher` (Task 5, ahora devuelve `list[dict]`);
  `encolar_pregunta_categoria` y `preguntar_siguiente_categoria` (Task 3).
- Produces: `bot.py::_iniciar_importacion(update, movimientos: list[dict])` — placeholder
  en este task (manda un mensaje temporal), reemplazado por el flujo real en
  Task 8. Esto permite verificar el camino de "un solo resultado" de punta a
  punta sin esperar al checklist completo.

**Nota de alcance:** el spec dice que la regla de "preguntar lo que falte" aplica
también al voucher simple. Acá se conecta la parte de **categoría** (Step 2,
abajo) porque la descripción de un voucher es texto libre del usuario y puede
caer en "Otros" igual que un gasto de texto. La parte de **medio** se deja afuera
a propósito: un voucher es, por definición, una foto de un pago que casi siempre
muestra el medio de forma explícita (el logo de Yape, el nombre del banco) — a
diferencia de una nota de voz, donde el usuario puede simplemente no mencionarlo.
Si en la práctica el OCR devuelve "No identificado" seguido, se puede sumar
después reusando el mismo `teclado_medio_gasto()`.

- [ ] **Step 1: Reescribir `handle_photo`**

Buscá la función completa (empieza en `async def handle_photo(update: Update,
context: ContextTypes.DEFAULT_TYPE):` y termina justo antes de `# ── Recibir
descripción pendiente`):

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"temp_{update.message.message_id}.jpg"
    await file.download_to_drive(file_path)

    try:
        await update.message.reply_text("⏳ Leyendo texto del voucher...")
        monto, medio, destinatario, fecha = procesar_voucher(file_path)

        if monto == "No detectado":
            await update.message.reply_text(
                "⚠️ No pude leer el monto del voucher.\n"
                "Asegúrate de que la imagen sea nítida.",
                reply_markup=menu_principal()
            )
            os.remove(file_path)
            return ConversationHandler.END

        descripcion = update.message.caption
        telegram_id = update.message.from_user.id

        if descripcion:
            await registrar_transaccion(update, telegram_id, monto, medio, destinatario, fecha, descripcion)
            os.remove(file_path)
            return ConversationHandler.END
        else:
            datos_pendientes[telegram_id] = {
                "monto": monto, "medio": medio,
                "destinatario": destinatario, "fecha": fecha,
            }
            await update.message.reply_text(
                f"📋 *Voucher leído:*\n"
                f"💰 Monto: S/ {monto}\n"
                f"📱 Medio: {medio}\n"
                f"👤 Destinatario: {destinatario}\n\n"
                f"¿A qué correspondió este gasto? Escribe una descripción breve.\n"
                f"_(Ej: almuerzo con amigos, uber al trabajo, consulta médica)_",
                parse_mode="Markdown"
            )
            os.remove(file_path)
            return ESPERANDO_DESCRIPCION

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error al procesar la imagen: {e}",
            reply_markup=menu_principal()
        )
        if os.path.exists(file_path):
            os.remove(file_path)
        return ConversationHandler.END
```

Reemplazala por:

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"temp_{update.message.message_id}.jpg"
    await file.download_to_drive(file_path)

    try:
        await update.message.reply_text("⏳ Leyendo la imagen...")
        movimientos = procesar_voucher(file_path)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error al procesar la imagen: {e}",
            reply_markup=menu_principal()
        )
        return ConversationHandler.END
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    movimientos = [m for m in movimientos if m.get("monto") != "No detectado"]
    if not movimientos:
        await update.message.reply_text(
            "⚠️ No pude leer ningún monto en la imagen.\n"
            "Asegúrate de que sea nítida.",
            reply_markup=menu_principal()
        )
        return ConversationHandler.END

    if len(movimientos) == 1:
        return await _procesar_voucher_simple(update, movimientos[0])

    return await _iniciar_importacion(update, movimientos)


async def _procesar_voucher_simple(update, item: dict):
    """Un solo movimiento leído: mismo comportamiento que el bot ya tenía para
    un voucher de Yape/Plin/depósito."""
    monto = item["monto"]
    medio = item["medio"]
    destinatario = item["destinatario"]
    fecha = item["fecha"]

    descripcion = update.message.caption
    telegram_id = update.message.from_user.id

    if descripcion:
        await registrar_transaccion(update, telegram_id, monto, medio, destinatario, fecha, descripcion)
        return ConversationHandler.END

    datos_pendientes[telegram_id] = {
        "monto": monto, "medio": medio,
        "destinatario": destinatario, "fecha": fecha,
    }
    await update.message.reply_text(
        f"📋 *Voucher leído:*\n"
        f"💰 Monto: S/ {monto}\n"
        f"📱 Medio: {medio}\n"
        f"👤 Destinatario: {destinatario}\n\n"
        f"¿A qué correspondió este gasto? Escribe una descripción breve.\n"
        f"_(Ej: almuerzo con amigos, uber al trabajo, consulta médica)_",
        parse_mode="Markdown"
    )
    return ESPERANDO_DESCRIPCION


async def _iniciar_importacion(update, movimientos: list[dict]):
    """Placeholder — el checklist real llega en la Task 8 de este plan."""
    await update.message.reply_text(
        f"📋 Leí {len(movimientos)} movimientos en la imagen. "
        "La importación por lotes todavía no está lista.",
        reply_markup=menu_principal(),
    )
    return ConversationHandler.END
```

- [ ] **Step 2: Conectar `registrar_transaccion` con la cola de categoría**

Buscá la función completa:

```python
async def registrar_transaccion(update, telegram_id, monto, medio, destinatario, fecha, descripcion):
    try:
        usuario_id = obtener_o_crear_usuario(telegram_id)
        categoria = clasificar_gasto(descripcion, usuario_id)
        emoji = EMOJIS_CATEGORIA.get(categoria, "📦")
        guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario, fecha)

        # Escapar caracteres especiales de Markdown en campos dinámicos
        def esc(text):
            for ch in ('_', '*', '`', '['):
                text = str(text).replace(ch, f'\\{ch}')
            return text

        await update.message.reply_text(
            f"✅ *Transacción registrada*\n\n"
            f"💰 Monto:         S/ {esc(monto)}\n"
            f"📱 Medio:          {esc(medio)}\n"
            f"👤 Destinatario:  {esc(destinatario)}\n"
            f"📅 Fecha:          {esc(fecha)}\n"
            f"📝 Descripción:   {esc(descripcion)}\n"
            f"{emoji} Categoría:    {esc(categoria)}\n\n"
            f"¿Qué deseas hacer ahora?",
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar: {e}", reply_markup=menu_principal())
```

Reemplazala por:

```python
async def registrar_transaccion(update, context, telegram_id, monto, medio, destinatario, fecha, descripcion):
    try:
        usuario_id = obtener_o_crear_usuario(telegram_id)
        categoria = clasificar_gasto(descripcion, usuario_id)
        emoji = EMOJIS_CATEGORIA.get(categoria, "📦")
        trans_id = guardar_transaccion(usuario_id, monto, medio, descripcion, categoria, destinatario, fecha)

        # Escapar caracteres especiales de Markdown en campos dinámicos
        def esc(text):
            for ch in ('_', '*', '`', '['):
                text = str(text).replace(ch, f'\\{ch}')
            return text

        await update.message.reply_text(
            f"✅ *Transacción registrada*\n\n"
            f"💰 Monto:         S/ {esc(monto)}\n"
            f"📱 Medio:          {esc(medio)}\n"
            f"👤 Destinatario:  {esc(destinatario)}\n"
            f"📅 Fecha:          {esc(fecha)}\n"
            f"📝 Descripción:   {esc(descripcion)}\n"
            f"{emoji} Categoría:    {esc(categoria)}\n\n"
            f"¿Qué deseas hacer ahora?",
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

        if categoria == "Otros":
            encolar_pregunta_categoria(telegram_id, trans_id, monto, descripcion)
            await preguntar_siguiente_categoria(context, update.effective_chat.id, telegram_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar: {e}", reply_markup=menu_principal())
```

Ahora actualizá los dos call sites. Dentro de `_procesar_voucher_simple` (la
función que escribiste en el Step 1 de este mismo task), buscá:

```python
    if descripcion:
        await registrar_transaccion(update, telegram_id, monto, medio, destinatario, fecha, descripcion)
        return ConversationHandler.END
```

Reemplazá por:

```python
    if descripcion:
        await registrar_transaccion(update, context, telegram_id, monto, medio, destinatario, fecha, descripcion)
        return ConversationHandler.END
```

Y `_procesar_voucher_simple` necesita recibir `context` para poder pasarlo — su
firma actual (del Step 1) es `async def _procesar_voucher_simple(update, item:
dict):`. Cambiala a `async def _procesar_voucher_simple(update, context, item:
dict):`, y en `handle_photo`, donde llamás
`return await _procesar_voucher_simple(update, movimientos[0])`, cambiá a
`return await _procesar_voucher_simple(update, context, movimientos[0])`.

Por último, en `handle_descripcion` (la función que recibe la descripción
cuando el usuario responde después de un voucher sin caption), buscá:

```python
    datos = datos_pendientes.pop(telegram_id)
    await registrar_transaccion(
        update, telegram_id,
        datos["monto"], datos["medio"], datos["destinatario"], datos["fecha"],
        descripcion
    )
    return ConversationHandler.END
```

Reemplazá por:

```python
    datos = datos_pendientes.pop(telegram_id)
    await registrar_transaccion(
        update, context, telegram_id,
        datos["monto"], datos["medio"], datos["destinatario"], datos["fecha"],
        descripcion
    )
    return ConversationHandler.END
```

- [ ] **Step 3: Verificación manual del caso de un solo resultado**

Mandale al bot una foto de un voucher Yape/Plin (con y sin caption, las dos
formas). Esperado: mismo comportamiento exacto que antes de este plan.

Mandale una foto de un voucher de depósito bancario. Esperado: se lee monto y
medio "Transferencia" (o lo que diga el voucher), y sigue el mismo flujo de
pedir descripción.

Mandale un voucher con una descripción ambigua que sepas que va a caer en
"Otros" (ej. una palabra sin relación con ninguna categoría). Esperado: se
registra en "Otros" y aparece la pregunta de categoría con botones.

- [ ] **Step 4: Commit**

```bash
git add bot/bot.py
git commit -m "handle_photo distingue voucher simple de import por lotes"
```

---

## Task 7: Deduplicación pura + consulta de apoyo

**Files:**
- Create: `bot/dedupe.py`
- Create: `bot/tests/test_dedupe.py`
- Modify: `bot/db.py`

**Interfaces:**
- Produces: `dedupe.marcar_duplicados(movimientos: list[dict], existentes: list[tuple[float, str]]) -> list[bool]`
  (pura, sin DB). `db.obtener_montos_fecha_rango(usuario_id: int, desde: str, hasta: str) -> list[tuple[float, str]]`
  (I/O, sin test — mismo criterio que el resto de `db.py`). Task 8 combina las
  dos: pide el rango de fechas del lote a `db.py` y se lo pasa a `dedupe.py`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `bot/tests/test_dedupe.py`:

```python
from dedupe import marcar_duplicados


def test_mismo_monto_y_fecha_marca_duplicado():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_monto_distinto_no_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(50.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_fecha_distinta_no_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-17")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_tolerancia_de_un_centavo():
    movimientos = [{"monto": 32.005, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True]


def test_diferencia_de_dos_centavos_no_marca():
    movimientos = [{"monto": 32.02, "fecha": "2026-08-18"}]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [False]


def test_lote_mixto_evalua_cada_uno_independiente():
    movimientos = [
        {"monto": 32.0, "fecha": "2026-08-18"},
        {"monto": 10.0, "fecha": "2026-08-14"},
    ]
    existentes = [(32.0, "2026-08-18")]
    assert marcar_duplicados(movimientos, existentes) == [True, False]


def test_sin_existentes_nada_se_marca():
    movimientos = [{"monto": 32.0, "fecha": "2026-08-18"}]
    assert marcar_duplicados(movimientos, []) == [False]
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

```bash
cd bot
python -m pytest tests/test_dedupe.py -v
```

Esperado: `ModuleNotFoundError: No module named 'dedupe'`.

- [ ] **Step 3: Crear `bot/dedupe.py`**

```python
"""
dedupe.py — FinanzasBot v3.1
Marca, sin tocar la base, qué movimientos de un lote importado ya podrían
estar registrados: mismo monto (±1 centavo) y misma fecha.

Deliberadamente NO compara texto/destinatario: dos fuentes distintas (una
captura de banco y lo que vos tipeaste a mano) casi nunca describen el mismo
movimiento con las mismas palabras, así que comparar texto da más falsos
negativos y positivos de los que evita.
"""

TOLERANCIA_MONTO = 0.01


def marcar_duplicados(movimientos: list[dict], existentes: list[tuple]) -> list[bool]:
    """True en la posición i si movimientos[i] coincide con algún existente.

    movimientos[i] necesita "monto" (float) y "fecha" ("YYYY-MM-DD").
    existentes es una lista de (monto: float, fecha: "YYYY-MM-DD") ya en la base.
    """
    resultado = []
    for m in movimientos:
        monto = float(m.get("monto", 0))
        fecha = m.get("fecha")
        coincide = any(
            fecha == f_ex and abs(monto - m_ex) <= TOLERANCIA_MONTO
            for m_ex, f_ex in existentes
        )
        resultado.append(coincide)
    return resultado
```

- [ ] **Step 4: Correr los tests y confirmar que pasan**

```bash
python -m pytest tests/test_dedupe.py -v
```

Esperado: los 7 tests en verde.

- [ ] **Step 5: Agregar la consulta de apoyo en `db.py`**

Al final de `bot/db.py`, después de `desvincular_web`, agregá:

```python


def obtener_montos_fecha_rango(usuario_id: int, desde: str, hasta: str) -> list[tuple]:
    """(monto, fecha 'YYYY-MM-DD') de gastos e ingresos del usuario en el rango.

    Se compara contra las dos tablas, no solo gastos: si ya existe un ingreso con
    ese mismo monto y fecha, también vale la pena que el checklist lo marque
    como sospechoso — es al usuario a quien le toca decidir si es coincidencia.
    """
    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT monto::numeric, to_char(fecha, 'YYYY-MM-DD') AS f
                FROM transacciones
                WHERE usuario_id=%s AND fecha::date BETWEEN %s AND %s
                UNION ALL
                SELECT monto::numeric, to_char(fecha, 'YYYY-MM-DD') AS f
                FROM ingresos
                WHERE usuario_id=%s AND fecha::date BETWEEN %s AND %s
                """,
                (usuario_id, desde, hasta, usuario_id, desde, hasta),
            )
            return [(float(m), f) for m, f in cur.fetchall()]
```

Sin test para esta función — es I/O directo a Postgres, mismo criterio que el
resto de `db.py`, que hoy no tiene ningún test.

- [ ] **Step 6: Commit**

```bash
git add bot/dedupe.py bot/tests/test_dedupe.py bot/db.py
git commit -m "Deduplicacion por monto+fecha para la importacion de historiales"
```

---

## Task 8: Checklist de importación por lotes

El task más grande del plan: junta el OCR multi-movimiento (Task 5), la
deduplicación (Task 7), y las colas de medio/categoría (Task 3) en el flujo
completo que pidió el usuario para las capturas de historial.

**Desviación deliberada del spec:** el diseño original decía "recién al final
se guardan todos", es decir, mantener los movimientos en memoria mientras se
resuelven todas las preguntas y recién ahí insertarlos. Este plan guarda cada
movimiento **apenas se confirma el checklist** (con su medio/categoría
provisorios) y recién después dispara las mismas preguntas de seguimiento que
ya construyó la Task 3 — el mecanismo de "guardar y patchear después" que el
bot ya usa para gastos de texto, en vez de inventar un segundo mecanismo de
"retener y guardar al final" solo para este flujo. El resultado que ve el
usuario es idéntico (nada entra a su historial sin que confirme el checklist
de duplicados primero, que es lo que realmente importa); lo que cambia es
cuándo, por dentro, se hace el INSERT.

**Files:**
- Modify: `bot/bot.py`

**Interfaces:**
- Consumes: `dedupe.marcar_duplicados`, `db.obtener_montos_fecha_rango` (Task 7);
  `encolar_pregunta_categoria`, `preguntar_siguiente_categoria`,
  `teclado_medio_gasto` (Task 3).

- [ ] **Step 1: Importar lo que falta**

Buscá:

```python
from db import (
    obtener_o_crear_usuario,
    guardar_transaccion,
```

Reemplazá por:

```python
from db import (
    obtener_o_crear_usuario,
    guardar_transaccion,
    obtener_montos_fecha_rango,
```

Buscá:

```python
from ocr import procesar_voucher
from audio import transcribir_audio
```

Reemplazá por:

```python
from ocr import procesar_voucher
from audio import transcribir_audio
from dedupe import marcar_duplicados
```

- [ ] **Step 2: Agregar el estado de la importación**

Buscá (agregado en Task 3):

```python
categoria_pendiente_cola = {}  # telegram_id -> [{"id", "monto", "descripcion"}, ...]
```

Agregá debajo:

```python
importacion_pendiente = {}  # telegram_id -> {"items": [...], "cuenta_id": int}
```

- [ ] **Step 3: Reemplazar el placeholder `_iniciar_importacion`**

Buscá (agregado en Task 6):

```python
async def _iniciar_importacion(update, movimientos: list[dict]):
    """Placeholder — el checklist real llega en la Task 8 de este plan."""
    await update.message.reply_text(
        f"📋 Leí {len(movimientos)} movimientos en la imagen. "
        "La importación por lotes todavía no está lista.",
        reply_markup=menu_principal(),
    )
    return ConversationHandler.END
```

Reemplazalo por:

```python
async def _iniciar_importacion(update, movimientos: list[dict]):
    """Arma el checklist: dedup contra el historial, todo destildado lo que
    pinta a repetido, todo lo demás tildado por defecto."""
    telegram_id = update.message.from_user.id
    usuario_id = obtener_o_crear_usuario(telegram_id)

    fechas = [m["fecha"] for m in movimientos]
    existentes = obtener_montos_fecha_rango(usuario_id, min(fechas), max(fechas))
    duplicados = marcar_duplicados(movimientos, existentes)

    items = [
        {**m, "duplicado": dup, "marcado": not dup}
        for m, dup in zip(movimientos, duplicados)
    ]
    importacion_pendiente[telegram_id] = {"items": items}

    await update.message.reply_text(
        _texto_checklist(items),
        parse_mode="Markdown",
        reply_markup=_teclado_checklist(items),
    )
    return ConversationHandler.END


def _texto_checklist(items: list[dict]) -> str:
    n_dup = sum(1 for it in items if it["duplicado"])
    texto = f"📋 *Encontré {len(items)} movimientos*\n"
    if n_dup:
        texto += f"_{n_dup} se parecen a algo que ya tenés registrado — quedaron destildados._\n"
    texto += "\nTocá cada uno para tildar o destildar, y confirmá abajo."
    return texto


def _teclado_checklist(items: list[dict]) -> InlineKeyboardMarkup:
    filas = []
    for i, it in enumerate(items):
        check = "☑️" if it["marcado"] else "☐"
        desc = (it["descripcion"] or it["destinatario"] or "").strip()[:24]
        etiqueta = f"{check} {it['fecha'][5:]} S/ {float(it['monto']):.2f} — {desc}"
        if it["duplicado"]:
            etiqueta += " ⚠️"
        filas.append([InlineKeyboardButton(etiqueta, callback_data=f"impchk_toggle_{i}")])

    marcados = sum(1 for it in items if it["marcado"])
    filas.append([
        InlineKeyboardButton(f"✅ Registrar los {marcados} marcados", callback_data="impchk_confirmar"),
        InlineKeyboardButton("❌ Cancelar", callback_data="impchk_cancelar"),
    ])
    return InlineKeyboardMarkup(filas)
```

- [ ] **Step 4: Agregar los callbacks del checklist**

En `handle_callback`, buscá el bloque agregado en Task 3:

```python
            if cola:
                await preguntar_siguiente_categoria(context, query.message.chat_id, telegram_id_cb)
```

Justo después (todavía antes de `# ── Eliminar transacción`), agregá:

```python
    # ── Checklist de importación por lotes ──────────────────────────────
    elif accion.startswith("impchk_toggle_"):
        idx = int(accion[len("impchk_toggle_"):])
        telegram_id_cb = query.from_user.id
        estado = importacion_pendiente.get(telegram_id_cb)
        if not estado or idx >= len(estado["items"]):
            await query.answer("Esta importación ya no está activa.", show_alert=True)
        else:
            estado["items"][idx]["marcado"] = not estado["items"][idx]["marcado"]
            await safe_edit(
                query,
                _texto_checklist(estado["items"]),
                parse_mode="Markdown",
                reply_markup=_teclado_checklist(estado["items"]),
            )

    elif accion == "impchk_cancelar":
        telegram_id_cb = query.from_user.id
        importacion_pendiente.pop(telegram_id_cb, None)
        await safe_edit(query, "Importación cancelada.", reply_markup=menu_principal())

    elif accion == "impchk_confirmar":
        telegram_id_cb = query.from_user.id
        estado = importacion_pendiente.pop(telegram_id_cb, None)
        if not estado:
            await query.answer("Esta importación ya no está activa.", show_alert=True)
        else:
            await _guardar_importacion(context, query.message.chat_id, telegram_id_cb, usuario_id, estado["items"])
```

- [ ] **Step 5: Agregar `_guardar_importacion`**

Justo después de `_teclado_checklist` (agregada en el Step 3), agregá:

```python
async def _guardar_importacion(context, chat_id: int, telegram_id: int, usuario_id: int, items: list[dict]) -> None:
    """Guarda los items marcados, encola las categorías dudosas, y pregunta el
    medio una sola vez si hizo falta para alguno."""
    from datetime import datetime

    marcados = [it for it in items if it["marcado"]]
    if not marcados:
        await context.bot.send_message(chat_id=chat_id, text="No marcaste ningún movimiento.")
        return

    cuenta_id = obtener_cuenta_principal(usuario_id)
    total = 0
    falta_medio = False

    for it in marcados:
        monto = it["monto"]
        descripcion = it["descripcion"] or f"Yape/Plin a {it['destinatario']}" if it["destinatario"] != "No detectado" else "Importado de captura"
        categoria = clasificar_gasto(descripcion, usuario_id)
        medio = it["medio"] if it["medio"] != "No identificado" else "Manual"
        if medio == "Manual":
            falta_medio = True

        try:
            fecha_dt = datetime.strptime(it["fecha"], "%Y-%m-%d")
        except Exception:
            fecha_dt = None

        trans_id = guardar_transaccion(
            usuario_id, monto=monto, medio=medio,
            descripcion=descripcion, categoria=categoria,
            destinatario=it["destinatario"], fecha_voucher=it["fecha"],
            fecha=fecha_dt, cuenta_id=cuenta_id,
        )
        if categoria == "Otros":
            encolar_pregunta_categoria(telegram_id, trans_id, monto, descripcion)
        total += float(monto)

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"✅ Registré {len(marcados)} movimientos por S/ {total:.2f}.\n\n"
            "_No importé ingresos de esta captura, si había — cárgalos desde el menú._"
        ),
        parse_mode="Markdown",
    )

    if falta_medio:
        await context.bot.send_message(
            chat_id=chat_id,
            text="¿Con qué medio pagaste los que no especificaste?",
            reply_markup=teclado_medio_gasto(),
        )
    if categoria_pendiente_cola.get(telegram_id):
        await preguntar_siguiente_categoria(context, chat_id, telegram_id)
```

Ojo con la línea de `descripcion`: Python evalúa
`A if cond else B if cond2 else C` de derecha a izquierda en precedencia, así que
`it["descripcion"] or f"Yape/Plin a {it['destinatario']}" if ... else "Importado..."`
agrupa como `it["descripcion"] or (f"..." if ... else "Importado...")` — es
decir, se usa la descripción del OCR si vino algo; si no vino y hay
destinatario, arma "Yape/Plin a X"; si no hay ninguna de las dos, cae en
"Importado de captura". Verificalo con el Step 6 antes de dar por bueno.

- [ ] **Step 6: Verificación manual completa**

Mandale al bot una captura de historial con al menos 4-5 movimientos, donde
sepas de antemano si alguno ya está en tu historial (para probar el aviso de
duplicado) y alguno tenga una descripción tipo "Yape a Fulano" (para probar que
termina preguntando categoría).

Esperado, en orden:
1. Aparece el checklist con los duplicados destildados y el aviso ⚠️.
2. Destildar/tildar un ítem actualiza el mensaje sin crear uno nuevo.
3. Al confirmar, se registran solo los marcados.
4. Si alguno quedó en "Otros", aparece la pregunta de categoría con botones.
5. `/historial` muestra los movimientos nuevos con los montos y fechas
   correctos.

- [ ] **Step 7: Commit**

```bash
git add bot/bot.py
git commit -m "Checklist de importacion: confirmar, guardar, y preguntar lo que falte"
```

---

## Verificación final

Antes de desplegar a producción:

```bash
cd bot
python -m pytest tests/ -v
```

Esperado: todos los tests en verde (Tasks 2 y 7).

Y una pasada manual completa por Telegram, en este orden, contra el bot de
pruebas:
1. Nota de voz con medio explícito → sin pregunta de medio.
2. Nota de voz sin medio → aparece la pregunta.
3. Voucher Yape/Plin de un solo pago → sin cambios de comportamiento.
4. Voucher de depósito bancario → se lee bien.
5. Captura de historial con duplicados reales → el checklist los detecta.
6. Un ítem sin categoría clara → termina preguntando.

Recién ahí, desplegar siguiendo el flujo ya documentado en `claude.md`
(`git pull && sudo systemctl restart finanzasbot` en el servidor del bot).
