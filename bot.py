import os
import logging
import json
from typing import Dict, Tuple, List
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

# Простое хранилище рекордов в памяти
# Ключ: (chat_id, message_id, user_id), значение: score
high_scores: Dict[Tuple[int, int, int], int] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
        [InlineKeyboardButton("🏆 Таблица рекордов", callback_data="highscores_global")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🎮 <b>Доступные команды:</b>\n"
        "/start - Запустить игру\n"
        "/game - Начать играть\n"
        "/top - Глобальная таблица рекордов\n"
        "/myrecord - Ваш лучший рекорд\n"
        "/help - Эта справка\n\n"
        "<b>Как игра работает с рекордами:</b>\n"
        "1. После завершения игры нажмите кнопку 'Отправить результат'\n"
        "2. Бот сохранит ваш рекорд через Telegram API\n"
        "3. Рекорды можно посмотреть в таблице"
    )
    await update.message.reply_html(help_text)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает глобальную таблицу рекордов (из памяти бота)"""
    if not high_scores:
        await update.message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
        return
    
    # Группируем по user_id, берем лучший результат для каждого пользователя
    user_best_scores: Dict[int, int] = {}
    for (_, _, user_id), score in high_scores.items():
        if user_id not in user_best_scores or score > user_best_scores[user_id]:
            user_best_scores[user_id] = score
    
    # Сортируем по убыванию счета
    sorted_users = sorted(user_best_scores.items(), key=lambda x: x[1], reverse=True)[:15]
    
    lines = ["🏆 <b>Глобальная таблица рекордов:</b>\n"]
    for i, (user_id, score) in enumerate(sorted_users, 1):
        try:
            user = await context.bot.get_chat(user_id)
            name = user.username or user.first_name or f"Игрок {user_id}"
        except:
            name = f"Игрок {user_id}"
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        lines.append(f"{medal} {i}. {name}: <b>{score}</b>")
    
    await update.message.reply_html("\n".join(lines))

async def myrecord_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает лучший рекорд пользователя"""
    user_id = update.effective_user.id
    user_scores = [score for (_, _, u_id), score in high_scores.items() if u_id == user_id]
    
    if user_scores:
        best_score = max(user_scores)
        await update.message.reply_html(
            f"🎯 <b>Ваш лучший рекорд:</b> <code>{best_score}</code>\n\n"
            f"Вы установили рекорд в <b>{len(user_scores)}</b> играх."
        )
    else:
        await update.message.reply_text("У вас пока нет сохраненных рекордов. Сыграйте в /game!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    # 1. Обработка данных от игры (результат)
    if query.data and query.game_short_name:
        try:
            data = json.loads(query.data)
            if 'score' in data:
                score = int(data['score'])
                
                if query.game_short_name == GAME_SHORT_NAME:
                    chat_id = query.message.chat.id
                    message_id = query.message.message_id
                    user_id = query.from_user.id
                    
                    # Сохраняем в памяти
                    key = (chat_id, message_id, user_id)
                    high_scores[key] = score
                    
                    # Сохраняем через Telegram API (для встроенной таблицы рекордов)
                    try:
                        await context.bot.set_game_score(
                            user_id=user_id,
                            score=score,
                            chat_id=chat_id,
                            message_id=message_id,
                            force=True  # Разрешаем обновлять рекорд
                        )
                        logger.info(f"Рекорд сохранен: пользователь {user_id}, счет {score}")
                        await query.answer(f"✅ Рекорд {score} сохранен!")
                    except Exception as e:
                        logger.error(f"Ошибка set_game_score: {e}")
                        await query.answer("⚠️ Рекорд сохранен локально, но не в Telegram")
                else:
                    await query.answer("Неизвестная игра")
            else:
                await query.answer("Нет поля 'score' в данных")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Ошибка парсинга данных игры: {e}")
            await query.answer("❌ Ошибка в данных игры")
        except Exception as e:
            logger.error(f"Ошибка обработки результата: {e}")
            await query.answer("❌ Ошибка сохранения рекорда")
        return
    
    # 2. Обработка нажатия на игровую кнопку (запуск игры)
    if query.game_short_name and not query.data:
        if query.game_short_name == GAME_SHORT_NAME:
            logger.info(f"Пользователь {query.from_user.id} запускает игру")
            await query.answer(url=GAME_URL)
        else:
            await query.answer("Игра не найдена")
        return
    
    # 3. Обработка обычных кнопок
    await query.answer()
    
    if query.data == "about":
        about_text = (
            "🎮 <b>3-In-A-Row Game Bot</b>\n\n"
            "Это демонстрационный бот с поддержкой рекордов через Telegram Games API.\n\n"
            "<b>Технологии:</b>\n"
            "• Игра: HTML5/CSS/JavaScript на GitHub Pages\n"
            "• Бот: Python + python-telegram-bot\n"
            "• Хостинг: bothost.ru\n\n"
            "<b>Исходный код:</b>\n"
            "• Игра: https://github.com/arsmitt/3-in-a-row\n"
            "• API: https://core.telegram.org/api/bots/games"
        )
        await query.message.reply_html(about_text)
    
    elif query.data == "highscores_global":
        # Показываем таблицу рекордов при нажатии кнопки
        if not high_scores:
            await query.message.reply_text("Рекордов пока нет! Будьте первым!")
            return
        
        user_best_scores: Dict[int, int] = {}
        for (_, _, user_id), score in high_scores.items():
            if user_id not in user_best_scores or score > user_best_scores[user_id]:
                user_best_scores[user_id] = score
        
        sorted_users = sorted(user_best_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        lines = ["🏆 <b>Таблица рекордов:</b>\n"]
        for i, (user_id, score) in enumerate(sorted_users, 1):
            try:
                user = await context.bot.get_chat(user_id)
                name = user.username or user.first_name or f"Игрок {user_id}"
            except:
                name = f"Игрок {user_id}"
            lines.append(f"{i}. {name}: <b>{score}</b>")
        
        await query.message.reply_html("\n".join(lines))

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("myrecord", myrecord_command))
    
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен с поддержкой рекордов!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
