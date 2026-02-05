import os
import logging
import json
from typing import Dict, Tuple, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, GameHighScore
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

# Хранилище рекордов
user_scores: Dict[int, Dict[int, int]] = {}  # chat_id -> {user_id: score}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
        [InlineKeyboardButton("🏆 Таблица рекордов", callback_data="highscores")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с игрой и кнопкой для открытия рекордов
    await update.message.reply_game(
        game_short_name=GAME_SHORT_NAME,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🎮 <b>Доступные команды:</b>\n"
        "/start - Запустить игру\n"
        "/game - Начать играть\n"
        "/top - Глобальная таблица рекордов\n"
        "/myrecord - Ваш лучший рекорд\n"
        "/help - Эта справка\n\n"
        "<b>Как играть:</b>\n"
        "1. Нажмите кнопку 'Play' чтобы начать игру\n"
        "2. После завершения игры результат автоматически сохранится\n"
        "3. Просмотрите таблицу рекордов через меню"
    )
    await update.message.reply_html(help_text)

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает глобальную таблицу рекордов"""
    if not user_scores:
        await update.message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
        return
    
    # Собираем лучшие результаты всех пользователей
    all_scores = []
    for chat_id in user_scores:
        for user_id, score in user_scores[chat_id].items():
            all_scores.append((user_id, score))
    
    # Группируем по user_id, берем лучший результат
    user_best: Dict[int, int] = {}
    for user_id, score in all_scores:
        if user_id not in user_best or score > user_best[user_id]:
            user_best[user_id] = score
    
    # Сортируем по убыванию
    sorted_scores = sorted(user_best.items(), key=lambda x: x[1], reverse=True)[:10]
    
    lines = ["🏆 <b>Глобальная таблица рекордов:</b>\n"]
    for i, (user_id, score) in enumerate(sorted_scores, 1):
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
    
    # Ищем лучший результат во всех чатах
    best_score = 0
    for chat_id in user_scores:
        if user_id in user_scores[chat_id]:
            score = user_scores[chat_id][user_id]
            if score > best_score:
                best_score = score
    
    if best_score > 0:
        await update.message.reply_html(
            f"🎯 <b>Ваш лучший рекорд:</b> <code>{best_score}</code> очков\n\n"
            f"Продолжайте в том же духе!"
        )
    else:
        await update.message.reply_text("У вас пока нет сохраненных рекордов. Сыграйте в /game!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    # 1. Обработка нажатия на игровую кнопку (запуск игры)
    if query.game_short_name:
        logger.info(f"Пользователь {query.from_user.id} запускает игру")
        await query.answer(url=GAME_URL)
        return
    
    # 2. Обработка данных от игры (результат)
    if query.data and query.data.startswith('game_result_'):
        try:
            # Парсим данные из формата: game_result_{chat_id}_{message_id}_{user_id}_{score}
            parts = query.data.split('_')
            if len(parts) >= 6:
                chat_id = int(parts[2])
                message_id = int(parts[3])
                user_id = int(parts[4])
                score = int(parts[5])
                
                # Сохраняем рекорд
                if chat_id not in user_scores:
                    user_scores[chat_id] = {}
                user_scores[chat_id][user_id] = score
                
                # Сохраняем через Telegram API
                try:
                    await context.bot.set_game_score(
                        user_id=user_id,
                        score=score,
                        chat_id=chat_id,
                        message_id=message_id,
                        force=True
                    )
                    logger.info(f"Рекорд сохранен: пользователь {user_id}, счет {score}")
                    
                    # Получаем и показываем таблицу рекордов
                    try:
                        high_scores = await context.bot.get_game_high_scores(
                            user_id=user_id,
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
                            
                            await query.message.reply_html("\n".join(lines))
                    except Exception as e:
                        logger.error(f"Ошибка получения таблицы рекордов: {e}")
                        await query.answer(f"✅ Рекорд {score} сохранен!")
                except Exception as e:
                    logger.error(f"Ошибка set_game_score: {e}")
                    await query.answer(f"⚠️ Рекорд {score} сохранен локально")
        except Exception as e:
            logger.error(f"Ошибка обработки результата: {e}")
            await query.answer("❌ Ошибка сохранения рекорда")
        return
    
    # 3. Обработка обычных кнопок
    await query.answer()
    
    if query.data == "about":
        about_text = (
            "🎮 <b>3-In-A-Row Game Bot</b>\n\n"
            "Классическая игра в стиле 'три в ряд' с поддержкой рекордов через Telegram Games API.\n\n"
            "<b>Как играть:</b>\n"
            "• Перемещайте фигуры, чтобы собрать 3+ одинаковых в ряд\n"
            "• Каждая фигура приносит очки\n"
            "• Используйте бонусы из магазина\n"
            "• Сохраняйте рекорды и соревнуйтесь с друзьями!\n\n"
            "<b>GitHub:</b> https://github.com/arsmitt/3-in-a-row"
        )
        await query.message.reply_html(about_text)
    
    elif query.data == "highscores":
        chat_id = query.message.chat.id
        message_id = query.message.message_id
        
        try:
            # Получаем таблицу рекордов через Telegram API
            high_scores = await context.bot.get_game_high_scores(
                user_id=query.from_user.id,
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
                
                await query.message.reply_html("\n".join(lines))
            else:
                await query.message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
        except Exception as e:
            logger.error(f"Ошибка получения таблицы рекордов: {e}")
            await query.message.reply_text("Таблица рекордов пока пуста. Сыграйте первым!")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("myrecord", myrecord_command))
    
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен с полной поддержкой рекордов!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
