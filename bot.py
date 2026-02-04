import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_SHORT_NAME = "Event3IR"
GAME_URL = "https://arsmitt.github.io/3-in-a-row/"

if BOT_TOKEN is None:
    logging.error("ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("ℹ️ О проекте", callback_data="about")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n/start - Запустить игру\n/game - Начать играть\n/help - Справка"
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главный обработчик всех callback-запросов"""
    query = update.callback_query
    
    # 1. Обработка игровой кнопки
    if query.game_short_name:
        if query.game_short_name == GAME_SHORT_NAME:
            logger.info(f"Пользователь {query.from_user.id} запускает игру")
            await query.answer(url=GAME_URL)
        else:
            await query.answer("Игра не найдена")
        return
    
    # 2. Обработка обычных кнопок
    await query.answer()  # Закрываем "часики"
    
    if query.data == "about":
        await query.message.reply_text(
            "3-In-A-Row Game Bot\n\n"
            "Бот демонстрирует интеграцию HTML5-игр в Telegram.\n"
            "Игра размещена на GitHub Pages: https://arsmitt.github.io/3-in-a-row/"
        )
    else:
        logger.warning(f"Неизвестный callback_data: {query.data}")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    
    # Один обработчик для всех callback-запросов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
