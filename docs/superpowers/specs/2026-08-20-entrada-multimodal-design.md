# Entrada multimodal del bot: audio, vouchers de depósito y capturas de historial

## Contexto

Hoy el bot registra gastos de dos formas: texto libre (`extraer_gastos` en
`gastos_manual.py`) y foto de un voucher Yape/Plin (`ocr.py` → `procesar_voucher`,
que asume **un solo movimiento** con exactamente estos campos: monto, medio,
destinatario, fecha).

El usuario pidió tres capacidades nuevas:

1. **Notas de voz** — "ayer me gasté 20 soles en comida, 10 en ropa, los pagué con
   yape" o "ayer gasté 30 en bebidas" (sin medio: el bot debe preguntar).
2. **Voucher de depósito bancario** (foto) — mismo espíritu que el voucher Yape/Plin
   actual, pero de un banco.
3. **Captura de historial** (Yape, Plin, o app del banco) — **varios movimientos en
   una sola imagen**, algunos con descripción clara ("Yape a Rosa" → hay que
   preguntar de qué fue) y el riesgo real de que ya estén registrados por otra vía.

Se probó en producción que `qwen3-asr-flash` transcribe correctamente el OGG/Opus
que manda Telegram (177 tokens por 11 segundos de audio), así que la vía de voz es
viable sin conversión de formato ni herramientas adicionales en el servidor.

## Decisión cerrada con el usuario

Ante una captura con varios movimientos, el bot **compara contra el historial por
monto y fecha**, muestra la lista con las coincidencias **destildadas** y una nota de
por qué, y dentro de las tildadas por defecto **pregunta lo que falte** (medio de
pago, categoría) antes de guardar nada. El usuario confirma con un botón.

## Alcance (YAGNI)

Dentro:
- Transcribir notas de voz y reusar el pipeline de texto existente.
- Extender `ocr.py` para reconocer vouchers de depósito bancario, con el mismo
  contrato de "un movimiento".
- Extraer **listas** de movimientos de una captura de historial.
- Detección de duplicados por (usuario, monto, fecha) contra `transacciones` e
  `ingresos`.
- Cola de preguntas de seguimiento (medio, categoría) para movimientos incompletos,
  reusando el patrón de teclados en línea que ya existe.

Fuera de alcance, a propósito:
- Corregir automáticamente el año de una fecha ambigua en la captura — se asume el
  año actual y el usuario corrige a mano si hace falta (`/historial` + edición ya
  existente).
- Deduplicación difusa por texto/destinatario — solo monto + fecha, que es lo que
  se puede leer de forma confiable en dos fuentes distintas sin falsos positivos.
- Persistir la cola de preguntas o el estado de importación en la base — vive en
  memoria del proceso, igual que `datos_pendientes` e `ingreso_pendiente` hoy. Si el
  bot se reinicia a mitad de una importación larga, se pierde y hay que reenviar la
  imagen. Documentado como trade-off aceptado, no un descuido.
- Reconocer ingresos dentro de una captura de historial (ej. que te transfieran
  plata) — v1 solo importa gastos. Los historiales de Yape/Plin mezclan entradas y
  salidas; distinguir de forma confiable "recibí" vs "pagué" en un layout de
  captura variable es un problema en sí mismo. Se deja para una iteración futura,
  con un aviso explícito en el mensaje de resultado ("los ingresos de esta captura
  no se importan, cárgalos con /start → Ingreso").

## Componentes nuevos

### 1. `bot/audio.py` (nuevo)

```python
def transcribir_audio(file_path: str) -> str:
    """OGG/Opus de Telegram → texto, vía qwen3-asr-flash."""
```

Un solo llamado a la API con `input_audio` en base64, igual que ya hace `ocr.py` con
imágenes. Sin dependencias nuevas (no hace falta `ffmpeg` ni `pydub`: el endpoint
acepta el contenedor OGG tal cual).

### 2. `bot/ocr.py` — de "un voucher" a "N movimientos"

`procesar_voucher` cambia de firma: en vez de devolver una tupla de 4 campos,
devuelve `list[dict]`. Un voucher simple (Yape/Plin/depósito) sigue siendo el caso
común: una lista de longitud 1. Una captura de historial es una lista de N.

```python
def procesar_voucher(file_path: str) -> list[dict]:
    """Cada dict: monto, medio, descripcion, destinatario, fecha (best-effort)."""
```

El prompt se reescribe para cubrir los tres tipos de imagen (voucher Yape/Plin,
voucher de depósito, captura de historial con tabla de movimientos) y para devolver
siempre un array JSON, nunca un objeto suelto. Esto es la extensión de mayor riesgo
técnico del diseño — el prompt actual es determinístico para un layout fijo; leer
una tabla de historial con capturas de distintos bancos/apps va a necesitar
iteración real contra imágenes de ejemplo, no solo diseño de prompt en el papel.

`handle_photo` se adapta para recorrer la lista en vez de desempacar 4 variables; el
camino de "un solo resultado sin ambigüedad" se comporta igual que hoy (pregunta la
descripción si falta, guarda, listo). Un resultado con más de un ítem entra al
flujo de importación por lotes (abajo).

### 3. Deduplicación (`bot/db.py`, función nueva)

```python
def buscar_posibles_duplicados(usuario_id: int, movimientos: list[dict]) -> list[bool]:
    """Para cada movimiento, True si ya existe una transacción del mismo usuario
    con monto igual (±0.01) y misma fecha (día)."""
```

Una sola consulta con los montos y fechas del lote, no N consultas — el lote de una
captura de historial puede traer 15-20 filas.

### 4. Cola de preguntas + checklist de importación (`bot/bot.py`)

Estado en memoria, keyed por `telegram_id`, mismo patrón que `datos_pendientes`:

```python
importacion_pendiente[telegram_id] = {
    "movimientos": [...],       # con flag "duplicado_sospechoso" y "marcado"
    "cuenta_id": ...,
}
```

**Paso 1 — checklist.** Se muestra la lista con inline keyboard: cada fila es un
botón toggle (☑/☐), los sospechosos de duplicado arrancan destildados con una nota
debajo. Botón final "Registrar los N marcados".

**Paso 2 — cola de preguntas.** Al confirmar, se recorren los movimientos marcados
que tengan medio o categoría ambiguos (categoría cayó en "Otros", o no hay
descripción más allá de "Yape a fulano"). Se pregunta **uno por vez** con teclado en
línea (mismo patrón que ya existe para el medio de pago en `_procesar_y_guardar_gastos`),
y recién al final se guardan todos.

**Regla de cuándo preguntar** (aplica también al audio y al voucher simple): se
pregunta el medio si no vino en el texto/imagen, y se pregunta la categoría solo si
el clasificador automático (`clasificar_gasto`) devuelve "Otros" — no se interrumpe
al usuario por cada gasto si el clasificador ya está seguro.

### 5. Notas de voz — sin componente nuevo de negocio

Un `MessageHandler(filters.VOICE, handle_voice)` que transcribe y pasa el texto
resultante a `_procesar_y_guardar_gastos`, el mismo camino que ya usa el texto
escrito. Esto es deliberado: la voz es una fuente de texto, no un flujo nuevo. El
manejo de "falta el medio de pago" ya existe ahí (guarda con medio="Manual" y ofrece
botones para corregirlo) — no hace falta reinventarlo.

Antes de registrar, se le muestra al usuario la transcripción cruda ("Te escuché
decir: ..."), para que pueda detectar un error de ASR antes de que se guarde mal.

## Flujo de datos por caso

```
Nota de voz ──▶ transcribir_audio ──▶ extraer_gastos (ya existe) ──▶ guardar
                                        (pregunta medio ya existe, vía botones)

Voucher simple ──▶ procesar_voucher [1 item] ──▶ pregunta descripción si falta
  (Yape/Plin/depósito)                             (ya existe) ──▶ guardar

Captura historial ──▶ procesar_voucher [N items] ──▶ dedup ──▶ checklist
                                                        │
                                          confirma ──▶ cola de preguntas
                                                        │
                                                  (medio/categoría faltantes)
                                                        ▼
                                                   guardar en lote
```

## Testing

- `audio.py`: prueba de humo contra la API real con un archivo de voz conocido
  (script manual, como se hizo para validar el endpoint — no se automatiza en CI
  porque depende de la red y de la cuota de Qwen).
- `ocr.py`: el prompt nuevo se valida con un puñado de imágenes reales guardadas
  como fixtures (voucher Yape, voucher depósito, captura de historial de al menos
  dos apps distintas), comparando el JSON extraído contra lo esperado a mano. Esto
  reemplaza los tests unitarios tradicionales porque lo que falla en OCR no es
  lógica, es la calidad de la extracción.
- `buscar_posibles_duplicados`: tests unitarios normales contra la base de test —
  mismo monto/fecha marca True, monto distinto o fecha distinta marca False, y un
  monto igual pero de *otro* usuario no debe contar.
- Cola de preguntas y checklist: se prueban a mano en Telegram (no hay test harness
  para `python-telegram-bot` en este proyecto hoy) — se agrega al final del ciclo de
  implementación, con una tanda real de fotos/audios enviados al bot de pruebas.

## Riesgos conocidos

- **Calidad del OCR de historiales.** Ninguna captura de banco/Yape tiene el mismo
  layout; el prompt puede funcionar bien en las pruebas y fallar con una app que no
  se probó. Mitigación: el checklist siempre muestra lo que se extrajo antes de
  guardar nada, así que un error de lectura se corrige a mano, no se cuela.
- **Estado en memoria.** Ya mencionado en "Fuera de alcance" — aceptado.
- **Costo de tokens.** Una captura de historial con 20 filas es una imagen más
  pesada de lo habitual; no se espera que sea significativo contra la cuota mensual,
  pero no se midió con una imagen real de 20 filas antes de escribir esto.
