import os
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.environ.get('BOT_TOKEN')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Используйте /game для открытия списка игр')

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаем кнопку для запуска игры
    keyboard = [
        [InlineKeyboardButton("🎮 Запустить Event3IR", url="https://github.com/arsmitt/3-in-a-row/blob/main/index.html")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Доступные игры:\n\nEvent3IR - игра "3 в ряд"\n\nНажмите кнопку ниже, чтобы открыть игру:',
        reply_markup=reply_markup
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("game", game_command))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
