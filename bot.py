import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === КОНФИГУРАЦИЯ ===
# Получаем токен бота из переменной окружения (безопасный способ)
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Ваши данные игры
GAME_SHORT_NAME = "Event3IR"  # game_short_name из BotFather
GAME_URL = "https://arsmitt.github.io/3-in-a-row/"  # URL вашей игры

# === ПРОВЕРКА КОНФИГУРАЦИИ ===
if BOT_TOKEN is None:
    logging.error("ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    logging.info("Убедитесь, что вы:")
    logging.info("1. На bothost.ru в настройках бота задали переменную BOT_TOKEN")
    logging.info("2. Для локального теста создали файл .env с содержимым: BOT_TOKEN='ваш_токен'")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ОБРАБОТЧИКИ КОМАНД ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - приветствие и кнопка запуска игры"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🎮 Играть в 3-In-A-Row!", callback_game=GAME_SHORT_NAME)],
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n"
        "Добро пожаловать в игру <b>3-In-A-Row</b> — классическую головоломку для всех возрастов!\n\n"
        "Нажми кнопку ниже, чтобы начать играть прямо в Telegram!",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "<b>Доступные команды:</b>\n"
        "/start - Запустить бота и начать игру\n"
        "/help - Показать эту справку\n"
        "/game - Начать играть сразу\n\n"
        "<b>Как играть?</b>\n"
        "Нажми кнопку \"🎮 Играть в 3-In-A-Row!\" и игра откроется прямо в Telegram.\n"
        "Ищи одинаковые элементы и собирай их по три в ряд!"
    )
    await update.message.reply_html(help_text)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /game - прямой запуск игры"""
    keyboard = [[InlineKeyboardButton("🎮 Запустить игру!", callback_game=GAME_SHORT_NAME)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажми кнопку, чтобы начать играть!", reply_markup=reply_markup)

async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатия на игровую кнопку"""
    query = update.callback_query
    # Отвечаем на запрос, передавая URL игры
    await query.answer(url=GAME_URL)
    logger.info(f"Пользователь {query.from_user.id} запустил игру")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на обычные кнопки"""
    query = update.callback_query
    await query.answer()  # Закрываем "часики" на кнопке
    
    if query.data == "about":
        await query.edit_message_text(
            text="<b>3-In-A-Row Game Bot</b>\n\n"
                 "Это демонстрационный бот, показывающий интеграцию HTML5-игр в Telegram.\n"
                 "Игра создана с использованием HTML/CSS/JavaScript и размещена на GitHub Pages.\n\n"
                 "Исходный код игры: https://github.com/arsmitt/3-in-a-row",
            parse_mode="HTML"
        )

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main() -> None:
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    
    # Регистрируем обработчики callback-запросов
    application.add_handler(CallbackQueryHandler(game_callback, pattern="^" + GAME_SHORT_NAME + "$"))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
