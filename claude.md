Responder siempre en idioma español

# FinanzasBot — Contexto del proyecto

Bot de Telegram para finanzas personales, mercado peruano (Yape/Plin).
Repo: rijav89/finanzas-bot (privado). Versión activa: v3.1.
Última actualización de este contexto: 2026-08-02.

## Infraestructura

**Servidor bot** (129.153.191.245)
- Usuario: ubuntu · OS: Ubuntu 22.04 · Shape: VM.Standard.E2.1.Micro (Oracle Cloud Always Free) · AD-2
- Key SSH: `E:\Proyectos\Finanzas Bot\ssh-key-2026-03-19.key`
- Servicio systemd: `finanzasbot` (`sudo systemctl restart finanzasbot`)
- Directorio: `/home/ubuntu/finanzas-bot`, venv en `/home/ubuntu/finanzas-bot/venv`
- Backups de versiones anteriores en `/home/ubuntu/finanzas-bot/Backup/`

**Servidor backend/panel** (150.136.170.92) — nuevo, recién instalado
- Usuario: ubuntu · OS: Ubuntu 24.04 · Shape: VM.Standard.E2.1.Micro (Oracle Cloud Always Free)
- Key SSH: `E:\Proyectos\Finanzas Bot\Keys\ssh-key-2026-08-02-backend.key`
- Estado: nginx + python3 + certbot instalados; pendiente configurar el panel web
- Nota: en Ubuntu 24.04 usar `python3 -m pip` o `pip install --break-system-packages`

**Base de datos**: Supabase (plan gratuito)
- Host: `aws-1-sa-east-1.pooler.supabase.com` · Puerto 5432 · DB `postgres`
- User: `postgres.kzgrexncynqxhlpeypuv` · SSL: require
- Supabase pausa proyectos inactivos tras 7 días — restaurar en supabase.com si el bot no conecta

## Stack del bot
- python-telegram-bot==21.9 (con job-queue)
- psycopg[binary] + psycopg_pool
- openai (cliente para Qwen vía API compatible OpenAI)
- python-dotenv, matplotlib, pillow, openpyxl, APScheduler

## IA — Qwen (Alibaba Cloud Model Studio, región Singapore)
- Endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
  (endpoint dedicado del workspace: `https://ws-bcynyj2i14cccmz6.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`)
- Texto/NLP: `qwen-plus` · OCR/Visión: `qwen-vl-plus`
- Free quota: 1,000,000 tokens por modelo, vence 2026-10-30. Stop-on-Exhaust activado.
- Variable env: `DASHSCOPE_API_KEY`

## Archivos del bot (`/home/ubuntu/finanzas-bot/`)
- `bot.py` — handler principal de Telegram
- `config.py` — variables de entorno
- `db.py` — conexión PostgreSQL (psycopg_pool)
- `ocr.py` — OCR de comprobantes Yape/Plin con qwen-vl-plus
- `categorias.py` — clasificación de gastos con qwen-plus
- `gastos_manual.py` — NLP: detección de intención, extracción de gastos/ingresos/transferencias
- `graficos.py` — generación de gráficos matplotlib
- `migrate.py` — migraciones de DB

`config.py` lee: `TOKEN`, `DB_CONFIG`, `GEMINI_API_KEY` (legacy, no se usa), `DASHSCOPE_API_KEY`, `QWEN_BASE_URL` (default el endpoint intl), `QWEN_MODEL_TEXT='qwen-plus'`, `QWEN_MODEL_OCR='qwen-vl-plus'`.

## Funcionalidades implementadas
- Registro de gastos por texto natural ("gasté 45 en taxi")
- Registro de ingresos con fecha histórica ("ayer me pagaron mi sueldo")
- OCR de comprobantes Yape/Plin (foto → datos extraídos)
- Categorización automática (14 categorías)
- Sistema de cuentas nombradas con aliases semánticos
- Transferencias entre cuentas
- Reportes y resúmenes, exportación a Excel

Menú principal (Reply Keyboard 3x2): Gasto / Ingreso, Cuentas / Resumen, Comprobante / Ajustes.

## Modelo de datos
- `ACCOUNTS`: id, user_id, name, type, balance, is_default, aliases[], created_at
- `TRANSACTIONS`: id, account_id, type, amount, category, note, transaction_date, created_at
- Cuenta "Principal" se crea automáticamente en `/start` con `is_default=true`.

## Account resolver (3 capas)
1. Match exacto por nombre/alias → registra directo
2. Match semántico vía Qwen → confirma con inline button
3. Sin match → usa cuenta default + sugiere crear cuenta
Aprendizaje: keywords confirmados se agregan automáticamente a `aliases[]`.

## Intenciones detectadas
REGISTRAR_GASTOS, INICIAR_REGISTRO, REGISTRAR_INGRESO, TRANSFERIR, VER_RESUMEN, VER_CATEGORIAS, VER_HISTORIAL, VER_SALDO, EXPORTAR, AYUDA, FUERA_DE_TEMA

## UX Telegram
- `sendChatAction("typing")` antes de cualquier llamada a Qwen
- Confirmaciones con inline keyboard antes de persistir
- Flujo OCR: foto → mensaje editable "Analizando..." → edit con resultado
- MarkdownV2 en todos los mensajes del bot
- Reply Keyboard persistente (`resize_keyboard=True`)

## Sistema de cuentas — diseño (pendiente de implementar completo)
1. Cuenta Principal auto-creada en `/start` (crítico)
2. Transferencias atómicas entre cuentas (crítico)
3. Saldo inicial al crear cuenta
4. Cache de aliases en memoria, Qwen como fallback
5. Aprendizaje automático de aliases por confirmación
6. Resumen desglosado por cuenta en `/resumen`
7. Alerta proactiva de saldo bajo configurable
8. Detección de pagos recurrentes (Fase 2)

## Panel web — próximo paso
Stack decidido: FastAPI (reutiliza `db.py`/`config.py` del bot) + HTML/Alpine.js (sin Node, sin build step) + Nginx + Let's Encrypt (certbot) + auth por token simple.

Funcionalidades planeadas: dashboard de resumen mensual, gestión de cuentas, historial de transacciones con filtros, configuración de alertas de saldo bajo, exportar a Excel.

Estado servidor backend: nginx + python3-venv + certbot instalados; pendiente crear venv, instalar FastAPI, configurar Nginx y SSL.

## Notas importantes
- Oracle Ampere A1 no disponible por capacity en la región (intentar de madrugada)
- Backup de archivos originales en `/home/ubuntu/finanzas-bot/Backup/`
- ⚠️ El repo tiene commiteada una service account key de Google Cloud (`sacred-footing-489922-n6-b393bec9efea.json`, proyecto legacy de Gemini) — no está en `.gitignore`. Pendiente decidir si rotarla/revocarla.

## Estructura local del proyecto (este equipo)
`E:\Proyectos\Finanzas Bot\dev\`
- `bot/` — clon del repo `rijav89/finanzas-bot` (rama `main`), código del bot de Telegram
- `panel-web/` — código del panel web (FastAPI + Alpine.js), aún por construir
- `claude.md` — este archivo

Git: usa el Git embebido de GitHub Desktop (`%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`), no hay Git instalado por separado en el PATH del sistema. Las credenciales de GitHub para `rijav89` ya están en el Credential Manager de Windows (`wincred`).
`.env` de `bot/` no existe en este equipo (está en `.gitignore`) — hay que recrearlo con los valores reales antes de correr el bot localmente.
