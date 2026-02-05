import os
import logging
import json
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

# Храним message_id сообщений с играми для каждого чата
game_messages = {}  # chat_id -> message_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Отправляем игру БЕЗ дополнительных кнопок - Telegram сам добавит кнопку рекордов
    message = await update.message.reply_game(game_short_name=GAME_SHORT_NAME)
    
    # Сохраняем ID сообщения для этого чата
    chat_id = update.message.chat.id
    game_messages[chat_id] = message.message_id
    
    logger.info(f"Игра отправлена в чат {chat_id}, сообщение {message.message_id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🎮 <b>3-In-A-Row Game</b>\n\n"
        "Классическая игра 'три в ряд'.\n\n"
        "<b>Как играть:</b>\n"
        "1. Нажми 'Play' чтобы начать\n"
        "2. Собирай фигуры по 3+ в ряд\n"
        "3. После игры результат сохранится автоматически\n"
        "4. Нажми '🏆 High scores' в сообщении с игрой чтобы увидеть таблицу рекордов\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать игру\n"
        "/game - Запустить игру\n"
        "/scores - Посмотреть таблицу рекордов\n"
        "/help - Справка"
    )
    await update.message.reply_html(help_text)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Просто отправляем игру (Telegram сам добавит кнопку рекордов)
    message = await update.message.reply_game(game_short_name=GAME_SHORT_NAME)
    
    # Сохраняем ID сообщения
    chat_id = update.message.chat.id
    game_messages[chat_id] = message.message_id

async def scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает таблицу рекордов для последней игры в этом чате"""
    chat_id = update.message.chat.id
    
    if chat_id not in game_messages:
        await update.message.reply_text(
            "Сначала запустите игру через /start или /game, "
            "затем нажмите '🏆 High scores' в сообщении с игрой."
        )
        return
    
    message_id = game_messages[chat_id]
    
    try:
        # Получаем встроенную таблицу рекордов Telegram
        high_scores = await context.bot.get_game_high_scores(
            user_id=update.effective_user.id,
            chat_id=chat_id,
            message_id=message_id
        )
        
        if high_scores:
            lines = ["🏆 <b>Таблица рекордов:</b>\n"]
            for i, hs in enumerate(high_scores[:10], 1):
                try:
                    user = await context.bot.get_chat(hs.user.id)
                    name = user.username or user.first_name or f"Игрок {hs.user.id}"
                except:
                    name = f"Игрок {hs.user.id}"
                medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
                lines.append(f"{medal} {i}. {name}: <b>{hs.score}</b>")
            
            await update.message.reply_html("\n".join(lines))
        else:
            await update.message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
            
    except Exception as e:
        logger.error(f"Ошибка получения таблицы рекордов: {e}")
        await update.message.reply_text("Таблица рекордов пока пуста. Сыграйте первым!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    # 1. Обработка данных от игры (результат)
    if query.data:
        try:
            # Пробуем распарсить JSON от игры
            game_data = json.loads(query.data)
            
            if 'score' in game_data:
                score = int(game_data['score'])
                user = query.from_user
                chat_id = query.message.chat.id
                message_id = query.message.message_id
                
                logger.info(f"Получен результат от {user.id} ({user.first_name}): {score} очков")
                
                # === КРИТИЧЕСКИ ВАЖНО: Сохраняем через Telegram API для встроенных рекордов ===
                try:
                    # force=True позволяет обновлять рекорд
                    # disable_edit_message=True - не менять сообщение с игрой
                    await context.bot.set_game_score(
                        user_id=user.id,
                        score=score,
                        chat_id=chat_id,
                        message_id=message_id,
                        force=True,
                        disable_edit_message=True
                    )
                    
                    logger.info(f"✅ Рекорд сохранен в Telegram: {user.first_name} - {score}")
                    await query.answer(f"✅ Ваш результат {score} сохранен!")
                    
                    # Обновляем сохраненный message_id для этого чата
                    game_messages[chat_id] = message_id
                    
                except Exception as e:
                    logger.error(f"Ошибка set_game_score: {e}")
                    
                    # Если ошибка "CHAT_ADMIN_REQUIRED" - значит, бот не администратор
                    if "CHAT_ADMIN_REQUIRED" in str(e):
                        await query.answer("❌ Бот должен быть администратором чата для сохранения рекордов")
                    else:
                        await query.answer("⚠️ Рекорд не сохранен")
                
                return
                
        except json.JSONDecodeError:
            # Это не JSON от игры, игнорируем
            pass
    
    # 2. Обработка нажатия на игровую кнопку (запуск игры)
    if query.game_short_name:
        logger.info(f"Пользователь {query.from_user.id} запускает игру")
        await query.answer(url=GAME_URL)
        return
    
    # 3. Обработка обычных callback_data кнопок
    await query.answer()
    
    if query.data == "about":
        about_text = (
            "🎮 <b>3-In-A-Row Game Bot</b>\n\n"
            "Игра с встроенной системой рекордов Telegram.\n"
            "После игры нажмите '🏆 High scores' в сообщении с игрой "
            "для просмотра таблицы рекордов.\n\n"
            "<b>GitHub:</b> https://github.com/arsmitt/3-in-a-row"
        )
        await query.message.reply_html(about_text)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("scores", scores_command))
    
    # Обработчик всех callback-запросов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен с поддержкой встроенных рекордов Telegram!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
