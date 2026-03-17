# ================================
# IMPORTS
# ================================
from telegram.ext import ConversationHandler

ESPERANDO_DESCRIPCION = 1
import os
import re
import pytesseract
from PIL import Image
import psycopg

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

# ================================
# CONFIGURACIÓN GENERAL
# ================================

# Ruta de Tesseract (Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ⚠ En producción esto debe ir en variable de entorno
TOKEN = "8031530747:AAGlqcEc9-Q98wC4pYFW3_YVzke4Nj2uiv8"

# ================================
# CONEXIÓN A BASE DE DATOS
# ================================

def get_connection():
    """
    Crea y devuelve una conexión a PostgreSQL.
    """
    return psycopg.connect(
        "host=127.0.0.1 port=5432 dbname=finanzasbot user=postgres password=Javier1301"
    )

# ================================
# LÓGICA DE BASE DE DATOS
# ================================

def obtener_o_crear_usuario(telegram_id):
    """
    Busca el usuario en la base.
    Si no existe, lo crea.
    Devuelve el id interno.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM usuarios WHERE telegram_id = %s",
        (telegram_id,)
    )
    usuario = cur.fetchone()

    if usuario is None:
        cur.execute(
            "INSERT INTO usuarios (telegram_id) VALUES (%s) RETURNING id",
            (telegram_id,)
        )
        usuario_id = cur.fetchone()[0]
    else:
        usuario_id = usuario[0]

    conn.commit()
    cur.close()
    conn.close()

    return usuario_id


def guardar_transaccion(usuario_id, monto, medio):
    """
    Inserta una nueva transacción en la base de datos.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO transacciones (usuario_id, monto, medio) VALUES (%s, %s, %s)",
        (usuario_id, monto, medio)
    )

    conn.commit()
    cur.close()
    conn.close()


def obtener_total_mes(usuario_id):
    """
    Devuelve el total gastado en el mes actual
    para el usuario indicado.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(monto), 0)
        FROM transacciones
        WHERE usuario_id = %s
        AND date_trunc('month', fecha) = date_trunc('month', NOW());
    """, (usuario_id,))

    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    return total

# ================================
# OCR Y PROCESAMIENTO
# ================================

def procesar_ocr(file_path):
    """
    Ejecuta OCR sobre la imagen y devuelve:
    - monto detectado
    - medio detectado
    """

    text = pytesseract.image_to_string(Image.open(file_path), lang="spa")

    print("OCR CRUDO:")
    print(text)

    # Limpieza básica de errores comunes OCR
    text_limpio = text.replace("S5/", "S/").replace("S5", "S")

    # Buscar número como posible monto
    monto_match = re.search(r"(\d{2,4}[.,]?\d{0,2})", text_limpio)

    if monto_match:
        monto = float(monto_match.group(1).replace(",", "."))
    else:
        monto = None

    # Detectar medio
    if "yape" in text.lower():
        medio = "Yape"
    elif "plin" in text.lower():
        medio = "Plin"
    else:
        medio = "No identificado"

    return monto, medio

# ================================
# HANDLERS DEL BOT
# ================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # OCR y detección del voucher (tu código actual)
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    # aquí iría tu código de descarga + OCR
    monto = 50
    medio = "Yape"

    descripcion = update.message.caption

    # Si NO hay descripción
    if descripcion is None:

        # guardamos temporalmente datos del voucher
        context.user_data["monto"] = monto
        context.user_data["medio"] = medio

        await update.message.reply_text(
            "📝 ¿En qué gastaste ese monto?"
        )

        return ESPERANDO_DESCRIPCION

    # Si SÍ hay descripción
    categoria = categorizar(descripcion)

    guardar_transaccion(update, monto, medio, descripcion, categoria)

    await update.message.reply_text(
        f"""✅ Transacción registrada

        Monto: S/{monto}
        Medio: {medio}
        Descripción: {descripcion}
        Categoría: {categoria}
        """
    )

    return ConversationHandler.END


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /resumen
    Devuelve el total del mes actual.
    """

    telegram_id = update.effective_user.id
    usuario_id = obtener_o_crear_usuario(telegram_id)

    total = obtener_total_mes(usuario_id)

    await update.message.reply_text(
        f"📊 Total gastado este mes: S/ {float(total):.2f}"
    )
    
 async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):

    descripcion = update.message.text

    monto = context.user_data["monto"]
    medio = context.user_data["medio"]

    categoria = categorizar(descripcion)

    guardar_transaccion(update, monto, medio, descripcion, categoria)

    await update.message.reply_text(
        f"""✅ Transacción registrada

        Monto: S/{monto}
        Medio: {medio}
        Descripción: {descripcion}
        Categoría: {categoria}
        """
    )

    return ConversationHandler.END

# ================================
# INICIALIZACIÓN DEL BOT
# ================================

def main():
    """
    Punto de entrada del programa.
    """
    app = ApplicationBuilder().token(TOKEN).build()

    # Handler para fotos
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Handler para /resumen
    app.add_handler(CommandHandler("resumen", resumen))
    
    conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.PHOTO, handle_photo)],

    states={
        ESPERANDO_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_descripcion)
        ],
    },

    fallbacks=[]
)

app.add_handler(conv_handler)
    
    print("Bot corriendo...")
    app.run_polling()


if __name__ == "__main__":
    main()