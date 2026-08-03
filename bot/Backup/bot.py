import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from config import TOKEN
from db import *
from ocr import leer_voucher
from categorias import categorizar


ESPERANDO_DESCRIPCION = 1


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)

    path = "temp.jpg"

    await file.download_to_drive(path)

    monto, medio = leer_voucher(path)

    descripcion = update.message.caption

    if descripcion is None:

        context.user_data["monto"] = monto
        context.user_data["medio"] = medio

        await update.message.reply_text(
            "📝 ¿En qué gastaste ese monto?"
        )

        os.remove(path)

        return ESPERANDO_DESCRIPCION

    categoria = categorizar(descripcion)

    telegram_id = update.message.from_user.id

    usuario_id = obtener_o_crear_usuario(telegram_id)

    guardar_transaccion(usuario_id, monto, medio, descripcion, categoria)

    await update.message.reply_text(
        f"""
✅ Transacción registrada

Monto: S/{monto}
Medio: {medio}
Descripción: {descripcion}
Categoría: {categoria}
"""
    )

    os.remove(path)

    return ConversationHandler.END


async def recibir_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):

    descripcion = update.message.text

    monto = context.user_data["monto"]
    medio = context.user_data["medio"]

    categoria = categorizar(descripcion)

    telegram_id = update.message.from_user.id

    usuario_id = obtener_o_crear_usuario(telegram_id)

    guardar_transaccion(usuario_id, monto, medio, descripcion, categoria)

    await update.message.reply_text(
        f"""
✅ Transacción registrada

Monto: S/{monto}
Medio: {medio}
Descripción: {descripcion}
Categoría: {categoria}
"""
    )

    return ConversationHandler.END


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):

    telegram_id = update.message.from_user.id

    usuario_id = obtener_o_crear_usuario(telegram_id)

    total = obtener_total_mes(usuario_id)

    await update.message.reply_text(
        f"📊 Total gastado este mes: S/{float(total):.2f}"
    )


def main():

    app = ApplicationBuilder().token(TOKEN).build()

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

    app.add_handler(CommandHandler("resumen", resumen))

    print("Bot corriendo...")

    app.run_polling()


if __name__ == "__main__":
    main()