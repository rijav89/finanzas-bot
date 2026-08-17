Responder siempre en idioma español

# FinanzasBot — Contexto del proyecto

Bot de Telegram para finanzas personales, mercado peruano (Yape/Plin).
Repo: rijav89/finanzas-bot (privado). Versión activa: v3.1.
Última actualización de este contexto: 2026-08-14.

## Infraestructura

**Servidor bot** (129.153.191.245)
- Usuario: ubuntu · OS: Ubuntu 22.04 · Shape: VM.Standard.E2.1.Micro (Oracle Cloud Always Free) · AD-2
- Key SSH: `E:\Proyectos\Finanzas Bot\Keys\ssh-key-2026-03-19.key`
- Servicio systemd: `finanzasbot` (`sudo systemctl restart finanzasbot`)
- Directorio: `/home/ubuntu/finanzas-bot`, venv en `/home/ubuntu/finanzas-bot/venv`
- Backups de versiones anteriores en `/home/ubuntu/finanzas-bot/Backup/`

**Servidor backend/panel** (150.136.170.92)
- Usuario: ubuntu · OS: Ubuntu 24.04 · Shape: VM.Standard.E2.1.Micro (Oracle Cloud Always Free)
- Key SSH: `E:\Proyectos\Finanzas Bot\Keys\ssh-key-2026-08-02-backend.key`
- Estado (2026-08-15): backend FastAPI desplegado en `/home/ubuntu/finanzas-bot/panel-web/backend` (snapshot vía `git archive` + scp, aún sin git clone), venv propio, `.env` con permisos 600
- Servicio systemd: `panel-api` (uvicorn 127.0.0.1:8000, MemoryMax=350M, hardening). ⚠️ Tiene `Environment=COOKIE_SECURE=false` TEMPORAL para pruebas locales sin HTTPS — quitar en F6 al configurar nginx+certbot
- Pendiente F6: nginx server block, certbot/SSL, rate limits, migración **005** (RLS — el número 004 ya lo tomó el catálogo de categorías), rotación password BD

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
- Endpoint activo (default en `config.py`, vía `QWEN_BASE_URL`): `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- Endpoint alternativo del workspace (no confirmado si está en uso activo — verificar antes de asumir): `https://ws-bcynyj2i14cccmz6.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`
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
- Categorización automática: 18 categorías de gasto y 7 de ingreso, definidas en `bot/categorias.py` con una pista de una línea cada una (sin la pista, Qwen confundía Servicios con Hogar). `clasificar_ingreso()` usa el catálogo de ingresos; antes los ingresos pasaban por el de gastos y caían siempre en «Otros»
- Sistema de cuentas nombradas con aliases semánticos
- Cuenta "Principal" auto-creada en `/start` con `is_default=true`
- Transferencias entre cuentas
- Reportes y resúmenes, exportación a Excel

Menú principal (Reply Keyboard 3x2): Gasto / Ingreso, Cuentas / Resumen, Comprobante / Ajustes.

## Modelo de datos
- `ACCOUNTS`: id, user_id, name, type, balance, is_default, aliases[], created_at
- `TRANSACTIONS`: id, account_id, type, amount, category, note, transaction_date, created_at

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

## Sistema de cuentas — mejoras pendientes (bot ya tiene la base funcionando)
1. Transferencias atómicas entre cuentas (crítico — verificar atomicidad real en `db.py`)
2. Saldo inicial al crear cuenta
3. Cache de aliases en memoria, Qwen como fallback
4. Resumen desglosado por cuenta en `/resumen`
5. Alerta proactiva de saldo bajo configurable
6. Detección de pagos recurrentes (Fase 2)

## Panel web — estado de implementación

- **F1 completa (2026-08-14)**: BD migrada con Alembic (baseline 001 + checks 002 + módulos nuevos 003). 10 tablas nuevas (categorias con seed de 15, vinculos_auth, codigos_vinculacion, deudas, cuotas_deuda, presupuestos, perfiles_financieros, metas, metas_ahorro, insights_ia), columnas aditivas en cuentas (tipo) y pagos_fijos (frecuencia/fecha_fin/auto_registrar/ultimo_registro). Las migraciones se corren desde el servidor del bot: `panel-web/backend/deploy/alembic_desde_bot_env.py` (lee DB_CONFIG del .env del bot, secretos nunca salen del servidor).
- **F2 completa y verificada E2E (2026-08-15)**: API core en `panel-web/backend/` — auth proxy GoTrue con cookies HttpOnly SameSite=Strict, validación JWT HS256+JWKS (el proyecto Supabase firma ES256), vinculación por código de un solo uso (sha256, TTL 10min), CRUD cuentas/gastos/ingresos, transferencias atómicas, dashboard con saldo histórico, guard CSRF (X-Requested-With), envelope {data,error}, 22 tests pytest (anti-IDOR incluidos). Usuario de prueba: test-panel@finanzasbot.dev vinculado al usuario ficticio telegram_id 999999 (usuario_id 28) — útil para probar F3.
- Supabase Auth: proyecto `kzgrexncynqxhlpeypuv`, publishable key en el .env del servidor del panel. Confirmación de email ACTIVADA (los usuarios se crean desde el dashboard, auto-confirmados). Usuario real: ricardo1332@hotmail.com (aún sin vincular a su telegram_id).
- **F3 completa (2026-08-15)**: SPA Vite+React+Tailwind desplegada (nginx sirve `dist/` en `/var/www/panel` + proxy `/api`). Bento Grid con dnd-kit, Sankey lazy (Nivo), paleta cmdk, captura Mad Libs (gasto/ingreso, fecha con atajos), mobile-first con bottom sheet que respeta el teclado virtual.
- **F4 backend completo (2026-08-16)**: módulos de categorías, presupuestos (con semáforo), deudas con cronograma de cuotas y pago atómico, ahorros con metas, recurrentes y perfil/metas. 28 rutas, 38 tests. Comando `/vincular` en el bot.
- **F4 frontend completo (2026-08-16)**: páginas de Presupuestos, Deudas, Ahorros y Recurrentes; rediseño completo según los mockups «Fondo» (tokens claro/oscuro, sidebar, captura por pasos, donuts); cache de 2 min y prefetch al pasar el cursor.
- **Categorías, widgets y Configuración (2026-08-17)** — migración **004**: columna `categorias.tipo` (`gasto`|`ingreso`|`ambos`), 18 categorías de gasto y 7 de ingreso, `Transporte` → `Transporte y vehiculo` (la migración arrastra los movimientos, porque la columna es TEXT sin FK). Widgets nuevos de últimos ingresos y tendencia de saldo a 6 meses, ambos dentro de la consulta única del dashboard. Pantalla `/configuracion` con CRUD de categorías propias y selector de tema. 43 tests.
- **Deudas y préstamos (2026-08-17)** — alcance decidido: el módulo se usa para préstamos **entre personas**, sin intereses y **sin cronograma de cuotas**. Los cuatro movimientos (entregar, recibir, cobrar, devolver) mueven el saldo pero **no cuentan como ingreso ni gasto**: un préstamo no es plata que ganaste, y contar las devoluciones duplicaría lo que ya registraste al comprar. Se implementa con la categoría de sistema `Prestamo` (tipo `ambos`), excluida de los totales igual que `Transferencia`.
- ⚠️ **Pendiente — préstamos en cuotas de una entidad financiera**: queda sin resolver cómo tratar un crédito bancario, donde sí hay intereses. La vía de cuotas (`generar_cuotas` + `pagar_cuota`) sigue funcionando como estaba, registrando la cuota como gasto de `Finanzas`; eso es **inconsistente a propósito** con la regla de arriba, hasta decidirlo. Separar capital de interés requeriría una columna `monto_prestado` que hoy no existe (el modelo solo guarda `monto_total`).
- Siguientes: F5 insights IA, F6 deploy nginx/SSL/RLS.

**F6 — dominio**: el usuario usará un **subdominio de una web que ya posee** (no hace falta comprar dominio). Definir el subdominio y apuntar un A record a 150.136.170.92 antes de correr certbot.

**Acceso temporal mientras no hay dominio**: túnel SSH `panel-web/abrir-panel.ps1` (con `-Lan` para entrar desde el celular). La IP LAN de la PC cambia por DHCP — verificar antes de usar.

## Panel web — arquitectura decidida (2026-08-14)

**Stack definitivo:**
- Backend: FastAPI (Python 3.12+), reutiliza modelos vía SQLAlchemy 2.0 (asyncpg) + Alembic para migraciones. Estrategia híbrida: ORM para CRUD, Raw SQL para queries analíticas.
- Frontend: Vite SPA (React) + TailwindCSS — **no** Next.js/SSR, por el límite de 1GB RAM del servidor del panel (un proceso Node persistente en modo SSR compite por memoria con FastAPI en la misma máquina). Librerías: `cmdk` (paleta de comandos), Nivo o Recharts (diagramas Sankey).
- Auth: Supabase Auth (reemplaza el plan anterior de "token simple"). JWT en HttpOnly cookies, SameSite=Strict — objetivo OWASP ASVS L2/L3.
- Infraestructura: Nginx + Let's Encrypt (certbot), ya instalados en el servidor backend.

**Decisión clave de coexistencia bot/web:** el bot sigue escribiendo directo con `telegram_id` vía service role key (bypasea RLS). La web usa Supabase Auth (`auth.uid`). Pendiente de diseñar: vínculo seguro `telegram_id` ↔ `auth.uid` cuando un usuario de Telegram se registra en la web, y Row Level Security en las tablas de Supabase que respete ambos caminos de escritura.

**Alcance:** uso personal por ahora, pero la arquitectura de Auth/RLS debe quedar preparada para multi-usuario a futuro sin rediseño mayor.

**Mobile-first:** la web debe funcionar al mismo nivel de prioridad en móvil que en desktop, pero con densidad de información distinta por diseño (no simplificación técnica):
- Desktop: dashboard panorámico con Bento Grid completo, Sankey y métricas simultáneas.
- Móvil: dashboard prioriza solo lo más crítico (balance, alertas, 1-2 métricas destacadas); el resto de la analítica detallada vive en Reportes, no en el dashboard.
- Paleta de comandos en móvil usa disparador táctil visible (no depende de Ctrl+K).
- Breakpoints: móvil < 640px, tablet 640-1024px, desktop > 1024px.

**Funcionalidades planeadas:** dashboard de resumen mensual (Bento Grid + Sankey), gestión de cuentas, historial de transacciones con filtros, formularios "Mad Libs" para captura manual, configuración de alertas de saldo bajo, exportar a Excel/PDF, módulos nuevos de Deudas/Préstamos, Ahorro, Pagos Recurrentes y Presupuestos, insights de IA vía cron semanal (Qwen).

**Nota:** el cron de insights debe usar timezone explícita `America/Lima`, no UTC implícito — ya hubo un bug de este tipo en el job de recordatorios del bot (disparaba a las 4am en vez de las 9am hora Perú).

## Notas importantes
- Oracle Ampere A1 no disponible por capacity en la región (intentar de madrugada)
- Backup de archivos originales en `/home/ubuntu/finanzas-bot/Backup/`
- ⚠️ El repo tiene commiteada una service account key de Google Cloud (`sacred-footing-489922-n6-b393bec9efea.json`, proyecto legacy de Gemini) — no está en `.gitignore`. Pendiente decidir si rotarla/revocarla.
- Gestión de secretos: variables de entorno únicamente, nunca en el repo — no negociable, dado el historial de exposición (service account key + PAT de GitHub, ver más abajo).

## Estructura local del proyecto (este equipo)
`E:\Proyectos\Finanzas Bot\dev\` es la raíz del repo `rijav89/finanzas-bot` (monorepo, reorganizado 2026-08-02):
- `bot/` — código del bot de Telegram (antes era la raíz del repo)
- `panel-web/` — código del panel web (FastAPI + Vite/React), aún por construir
- `claude.md` — este archivo

Git: usa el Git embebido de GitHub Desktop (`%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`), no hay Git instalado por separado en el PATH del sistema. Las credenciales de GitHub para `rijav89` ya están en el Credential Manager de Windows (`wincred`).
`.env` de `bot/` no existe en este equipo (está en `.gitignore`) — hay que recrearlo con los valores reales antes de correr el bot localmente.

## Deploy en producción (servidor bot, 129.153.191.245)
Ajustado 2026-08-03 para el monorepo:
- `/home/ubuntu/finanzas-bot/` sigue siendo la raíz del repo git (mismo `git pull`)
- El código ahora queda en `/home/ubuntu/finanzas-bot/bot/` tras el pull
- `.env` y `venv/` permanecen en la raíz (`/home/ubuntu/finanzas-bot/.env` y `/home/ubuntu/finanzas-bot/venv/`), no se movieron — no están en git
- `/etc/systemd/system/finanzasbot.service` actualizado: `WorkingDirectory=/home/ubuntu/finanzas-bot/bot`, `EnvironmentFile` y `ExecStart` (venv) siguen apuntando a rutas absolutas en la raíz
- Backup pre-migración en `/home/ubuntu/finanzas-bot-backup-20260803.tar.gz`
- Flujo de deploy futuro: `cd /home/ubuntu/finanzas-bot && git pull && sudo systemctl restart finanzasbot`


⚠️ **Nota**: se encontraron y rescataron cambios de producción nunca commiteados (la migración completa a Qwen en `categorias.py`, `config.py`, `gastos_manual.py`, `ocr.py`) — ya están en GitHub. Quedaron además unos archivos `.save` sueltos en el servidor (`.env.save`, `gastos_manual.py.save`) de ediciones manuales anteriores, sin revisar.