import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GAME_SHORT_NAME = "Event3IR"
GAME_URL = "https://arsmitt.github.io/3-in-a-row/"

# === ПРОВЕРКА ===
if BOT_TOKEN is None:
    logging.error("ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ОБРАБОТЧИКИ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start - отправляем сообщение с кнопкой"""
    keyboard = [
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем игру с помощью send_game
    await update.message.reply_game(
        game_short_name=GAME_SHORT_NAME,
        reply_markup=reply_markup  # Дополнительные кнопки можно добавить здесь
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Запустить игру\n"
        "/game - Начать играть\n"
        "/help - Справка"
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /game - отправляем игру без дополнительных кнопок"""
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)

async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия на игровую кнопку в сообщении"""
    query = update.callback_query
    await query.answer(url=GAME_URL)
    logger.info(f"Пользователь {query.from_user.id} запустил игру")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик обычных кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        await query.message.reply_text(
            "3-In-A-Row Game Bot\n\n"
            "Бот демонстрирует интеграцию HTML5-игр в Telegram.\n"
            "Игра размещена на GitHub Pages."
        )

# === ЗАПУСК ===
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    
    # Обработчик нажатий на игровую кнопку
    application.add_handler(CallbackQueryHandler(game_callback, pattern="^" + GAME_SHORT_NAME + "$"))
    # Обработчик остальных callback-запросов
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
