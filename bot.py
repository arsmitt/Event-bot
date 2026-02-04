import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get('BOT_TOKEN')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Используйте /game для открытия списка игр')

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Отправляем игру напрямую
    await context.bot.send_game(
        chat_id=update.effective_chat.id,
        game_short_name="Event3IR"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("game", game_command))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
