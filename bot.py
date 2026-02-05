import os
import logging
import json
from typing import Dict, List
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

# Хранилище рекордов для команд /top и /myrecord
global_high_scores: Dict[int, Dict[str, any]] = {}  # user_id -> {name, best_score, games_played}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
        [InlineKeyboardButton("🏆 Таблица рекордов", callback_data="highscores")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
    """Показывает глобальную таблицу рекордов из памяти бота"""
    if not global_high_scores:
        await update.message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
        return
    
    # Сортируем по лучшему счету
    sorted_scores = sorted(
        global_high_scores.items(),
        key=lambda x: x[1]['best_score'],
        reverse=True
    )[:10]
    
    lines = ["🏆 <b>Глобальная таблица рекордов:</b>\n"]
    for i, (user_id, data) in enumerate(sorted_scores, 1):
        name = data['name']
        score = data['best_score']
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        lines.append(f"{medal} {i}. {name}: <b>{score}</b> (игр: {data['games_played']})")
    
    await update.message.reply_html("\n".join(lines))

async def myrecord_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает лучший рекорд пользователя"""
    user_id = update.effective_user.id
    
    if user_id in global_high_scores:
        data = global_high_scores[user_id]
        await update.message.reply_html(
            f"🎯 <b>Ваша статистика:</b>\n\n"
            f"Лучший рекорд: <b>{data['best_score']}</b>\n"
            f"Всего игр: <b>{data['games_played']}</b>\n"
            f"Имя: <b>{data['name']}</b>"
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
    if query.data:
        try:
            # Пробуем распарсить JSON из игры
            game_data = json.loads(query.data)
            
            if 'score' in game_data:
                score = int(game_data['score'])
                user = query.from_user
                chat_id = query.message.chat.id
                message_id = query.message.message_id
                
                logger.info(f"Получен результат от {user.id}: {score} очков")
                
                # === СОХРАНЕНИЕ РЕКОРДА В TELEGRAM API ===
                try:
                    # Важно: используем force=True, чтобы всегда обновлять рекорд
                    await context.bot.set_game_score(
                        user_id=user.id,
                        score=score,
                        chat_id=chat_id,
                        message_id=message_id,
                        force=True  # Разрешаем обновлять рекорд
                    )
                    
                    # === СОХРАНЕНИЕ В ЛОКАЛЬНОМ ХРАНИЛИЩЕ ===
                    user_id = user.id
                    user_name = user.username or user.first_name or f"Игрок {user.id}"
                    
                    if user_id not in global_high_scores:
                        global_high_scores[user_id] = {
                            'name': user_name,
                            'best_score': score,
                            'games_played': 1
                        }
                    else:
                        # Обновляем лучший результат, если текущий больше
                        if score > global_high_scores[user_id]['best_score']:
                            global_high_scores[user_id]['best_score'] = score
                        global_high_scores[user_id]['games_played'] += 1
                    
                    logger.info(f"Рекорд сохранен: {user_name} - {score}")
                    await query.answer(f"✅ Ваш результат {score} сохранен!")
                    
                except Exception as e:
                    logger.error(f"Ошибка set_game_score: {e}")
                    await query.answer("⚠️ Рекорд не сохранен в таблицу Telegram")
                
                return
                
        except json.JSONDecodeError:
            # Если не JSON, то это обычный callback_data
            pass
        except Exception as e:
            logger.error(f"Ошибка обработки данных игры: {e}")
            await query.answer("❌ Ошибка обработки результата")
            return
    
    # 3. Обработка обычных кнопок
    await query.answer()
    
    if query.data == "about":
        about_text = (
            "🎮 <b>3-In-A-Row Game Bot</b>\n\n"
            "Классическая игра в стиле 'три в ряд' с автоматическим сохранением рекордов.\n\n"
            "Рекорды сохраняются сразу после завершения игры.\n"
            "Для просмотра таблицы рекордов нажмите кнопку ниже."
        )
        await query.message.reply_html(about_text)
    
    elif query.data == "highscores":
        # Показать таблицу рекордов из памяти
        await show_highscores(query.message, context)

async def show_highscores(message, context):
    """Показать таблицу рекордов"""
    try:
        # Пробуем получить встроенную таблицу рекордов Telegram
        high_scores = await context.bot.get_game_high_scores(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        if high_scores:
            lines = ["🏆 <b>Таблица рекордов (встроенная):</b>\n"]
            for i, hs in enumerate(high_scores[:10], 1):
                try:
                    user = await context.bot.get_chat(hs.user.id)
                    name = user.username or user.first_name or f"Игрок {hs.user.id}"
                except:
                    name = f"Игрок {hs.user.id}"
                medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
                lines.append(f"{medal} {i}. {name}: <b>{hs.score}</b>")
            
            await message.reply_html("\n".join(lines))
            return
            
    except Exception as e:
        logger.warning(f"Встроенная таблица пуста или недоступна: {e}")
    
    # Если встроенной таблицы нет, показываем нашу
    if not global_high_scores:
        await message.reply_text("🏆 Рекордов пока нет! Будьте первым!")
        return
    
    sorted_scores = sorted(
        global_high_scores.items(),
        key=lambda x: x[1]['best_score'],
        reverse=True
    )[:10]
    
    lines = ["🏆 <b>Таблица рекордов (локальная):</b>\n"]
    for i, (user_id, data) in enumerate(sorted_scores, 1):
        name = data['name']
        score = data['best_score']
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🔸"))
        lines.append(f"{medal} {i}. {name}: <b>{score}</b>")
    
    await message.reply_html("\n".join(lines))

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("myrecord", myrecord_command))
    
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен с автоматическим сохранением рекордов!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
