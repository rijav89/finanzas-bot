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
- Servicio systemd: `panel-api` (uvicorn 127.0.0.1:8000, MemoryMax=350M, hardening). `COOKIE_SECURE=false` ya se quitó: la cookie va Secure desde que hay HTTPS.
- **F6 (2026-08-19/20)**: **el panel vive en https://finanzas.indexcom.pe**. Certificado Let's Encrypt por webroot (`certonly`), renovación con `certbot.timer` + hook de despliegue que recarga nginx — sin ese hook el certificado se renueva en disco y nginx sigue sirviendo el viejo hasta que vence. nginx en dos bloques: el 80 solo atiende el desafío ACME y redirige al **nombre** (no a `$host`: entrando por IP el navegador chocaría con un certificado que no la cubre), el 443 sirve el panel. Cabeceras, proxy y TLS en `deploy/snippets/` incluidos, porque nginx descarta todos los `add_header` heredados en cuanto un `location` declara el suyo. HSTS a un año sin preload. TLS 1.2/1.3, solo ECDHE, sin tickets, con OCSP stapling; sin `dhparam` a propósito (solo sirve para cifrados DHE). Hecho también: rate limits (10 r/s API, 5 r/min login), swap 1 GB con `swappiness=10`, backup semanal `deploy/backup_bd.sh` (pg_dump 17 del repo PGDG porque Supabase corre 17.6; rota a 8 semanas, domingos 04:00 Lima), rol `panel_web` de privilegio mínimo (migración 007), y puertos 80/443 abiertos en iptables y en la security list de Oracle.
- ⚠️ **DNS**: el subdominio tenía **dos** registros A —el nuestro y `69.46.28.218`, el hosting de indexcom.pe— y el tráfico alternaba entre ambos. Ya quedó uno solo. El resolutor de la red local puede tardar en soltar la caché; los públicos (8.8.8.8, 1.1.1.1) ya devuelven solo `150.136.170.92`.
- ⚠️ **Pendiente de F6**: rotar password de BD y clave anónima en el dashboard de Supabase (la ventana de la API pública estuvo abierta desde la migración 003). Al rotar la de BD hay que actualizar `ALEMBIC_DATABASE_URL` del panel y el `.env` del bot; la de `panel_web` es independiente y no se toca.
- Decisión sobre RLS (2026-08-19): las políticas de la 007 son **permisivas a propósito** (`USING (true)`). Filtrar por `usuario_id` en la base exigiría un `SET LOCAL` por transacción = **+150 ms por petición** (medido), y **no protege de un `.env` robado**: quien tenga la credencial fija el GUC él mismo. Hoy el aislamiento lo dan los filtros de cada query y los tests anti-IDOR. Con varios usuarios reales, el cambio es reemplazar `USING (true)` por `usuario_id = current_setting('app.usuario_id')::int`; `_fijar_guc_rls` ya espera detrás de `RLS_ACTIVO`.

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
- **F5 insights IA (2026-08-18)**: `analytics/insights.py` pre-agrega ~40 números (4 meses de historia, categorías del mes vs promedio previo, presupuestos, saldo, deuda, recurrentes) y **todas las cifras derivadas** —promedio, meses de colchón— se calculan en Python: cuando se le pidió dividir, qwen-plus devolvió S/ 222.00 donde iban S/ 188.67. El prompt prohíbe cifras que no estén textualmente en los datos. Salida validada con Pydantic estricto (máx 5), 1 reintento. `jobs/generar_insights.py` (flags `--usuario` y `--seco`) y `jobs/keepalive_supabase.py`, ambos en el crontab del servidor del panel — horas convertidas a UTC a mano porque `TZ=` en crontab no cambia la hora de disparo. `GET /insights` + `PATCH` leído; cero IA en el request path. 58 tests.
- ⚠️ La `DASHSCOPE_API_KEY` del `.env` del panel estaba **vacía** (solo el nombre). Se copió desde el `.env` del servidor del bot vía pipe ssh→ssh, sin que el valor tocara disco intermedio.
- **Dashboard reordenado (2026-08-19)**: seis widgets — saldo total (con variación vs cierre del mes pasado y miniatura de 6 meses solo en móvil), ingresos, gastos, tendencia de saldo (solo escritorio), últimos registros e insights. Los cinco primeros salvo tendencia se ven también en móvil. **Se eliminaron «Flujo del mes» y «Por categoría»**: ingresos y gastos son sus dos mitades, y con ellos se borró `@nivo/sankey` (216 kB, 74 gz). Backend: `ultimos_movimientos` (UNION de gastos e ingresos) reemplaza a `ultimos_ingresos`, y `promedio_previos` (3 meses sin el actual) alimenta las pastillas «vs promedio». `bentoStore` va en `version: 2` con `migrate` que resetea el orden guardado.
- **F5 completa — reportes y export (2026-08-19)**: `GET /reportes/resumen` con rango, tipo, cuenta y categoría, agrupable por categoria/mes/cuenta; cada fila trae ingresos y gastos por separado. Export `.xlsx` y `.pdf` con los mismos filtros (resumen + detalle, tope 5000 filas), **un archivo a la vez** por semáforo y armado en `to_thread` porque openpyxl/reportlab son sincrónicos. Página `/reportes` con atajos de rango. El helper `descargar()` del cliente va por fetch+blob para que un error llegue como ApiError y no reemplace la pestaña por un JSON. 67 tests.
- ⚠️ **Aviso de seguridad de Supabase resuelto (2026-08-19), migración 006**: los roles `anon`/`authenticated` tenían SELECT/INSERT/UPDATE/DELETE sobre las 16 tablas de `public` y once no tenían RLS — `insights_ia`, `vinculos_auth`, `codigos_vinculacion` y `categorias` devolvían filas por HTTP a cualquiera con la URL del proyecto. Lo grave era el INSERT en `vinculos_auth`: permitía atar una cuenta de Auth ajena a un `usuario_id` y leer esas finanzas por la vía legítima del panel. Se activó RLS en todas y se hizo REVOKE + ALTER DEFAULT PRIVILEGES. El rol `postgres` (bot y panel) tiene BYPASSRLS, así que no cambió nada para ellos. **Pendiente: rotar password de BD y clave anónima** — la ventana estuvo abierta desde la migración 003.
- Siguientes: terminar F5 (reportes + export), F6 deploy nginx/SSL/RLS.

**F6 — dominio**: el usuario usará un **subdominio de una web que ya posee** (no hace falta comprar dominio). Definir el subdominio y apuntar un A record a 150.136.170.92 antes de correr certbot.

**Acceso**: https://finanzas.indexcom.pe desde cualquier dispositivo. El túnel SSH `panel-web/abrir-panel.ps1` quedó obsoleto — el puerto 80 ahora redirige a HTTPS, así que ya no sirve para ver el panel.

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