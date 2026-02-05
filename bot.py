import os
import logging
import json
from telegram import Update
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
    """Обработчик команды /start - только приветствие, без игры"""
    welcome_text = (
        "🎮 Добро пожаловать в 3-In-A-Row бота!\n\n"
        "Используйте команду /game чтобы начать играть.\n"
        "После игры результаты автоматически сохранятся, "
        "и в сообщении с игрой появится таблица рекордов (Top Players)."
    )
    await update.message.reply_text(welcome_text)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /game - отправляет игру"""
    # Отправляем игру без дополнительных кнопок
    # Telegram автоматически добавит кнопку "Play GameName" и позже кнопку рекордов
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик всех callback-запросов"""
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
                
                # Ключевой момент: сохраняем рекорд с ВКЛЮЧЕННЫМ обновлением сообщения
                try:
                    await context.bot.set_game_score(
                        user_id=user.id,
                        score=score,
                        chat_id=chat_id,
                        message_id=message_id,
                        force=True,  # Разрешаем обновлять рекорд
                        disable_edit_message=False  # ВАЖНО: разрешаем Telegram редактировать сообщение!
                    )
                    
                    logger.info(f"✅ Рекорд сохранен: {user.first_name} - {score}")
                    
                    # Получаем обновленную таблицу рекордов
                    try:
                        high_scores = await context.bot.get_game_high_scores(
                            user_id=user.id,
                            chat_id=chat_id,
                            message_id=message_id
                        )
                        
                        if high_scores:
                            # Логируем для отладки
                            logger.info(f"Текущие рекорды: {[(hs.user.id, hs.score) for hs in high_scores[:3]]}")
                            
                    except Exception as e:
                        logger.warning(f"Не удалось получить рекорды: {e}")
                    
                    await query.answer(f"✅ Ваш результат {score} сохранен!")
                    
                except Exception as e:
                    logger.error(f"Ошибка set_game_score: {e}")
                    # Если ошибка "CHAT_ADMIN_REQUIRED" - бот не администратор
                    if "CHAT_ADMIN_REQUIRED" in str(e):
                        await query.answer("❌ Бот должен быть администратором чата для сохранения рекордов")
                    else:
                        await query.answer("⚠️ Ошибка сохранения рекорда")
                
                return
                
        except json.JSONDecodeError:
            # Это не JSON от игры, игнорируем
            pass
        except Exception as e:
            logger.error(f"Ошибка обработки данных игры: {e}")
            await query.answer("❌ Ошибка обработки результата")
            return
    
    # 2. Обработка нажатия на игровую кнопку (запуск игры)
    if query.game_short_name:
        logger.info(f"Пользователь {query.from_user.id} запускает игру")
        await query.answer(url=GAME_URL)
        return
    
    # 3. Любые другие callback-запросы
    await query.answer()

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("game", game_command))
    
    # Обработчик всех callback-запросов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен! Команда /start - приветствие, /game - запуск игры с рекордами.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
