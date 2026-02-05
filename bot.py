import os
import logging
import json
import sqlite3
from datetime import datetime
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

# ===== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ДЛЯ РЕЙТИНГА =====
def init_database():
    """Создаем базу данных для хранения рейтингов игроков"""
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    
    # Таблица для хранения всех результатов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            score INTEGER NOT NULL,
            game_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Индексы для быстрого поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON user_scores(score DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON user_scores(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON user_scores(created_at DESC)')
    
    # Таблица для хранения лучших результатов каждого пользователя
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_best_scores (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            best_score INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            last_played TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных для рейтинга инициализирована")

# Инициализируем БД при запуске
init_database()

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ =====
def save_score_to_db(user_id, username, first_name, score, game_time=None):
    """Сохраняет результат игры в базу данных"""
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    
    # Сохраняем в историю всех игр
    cursor.execute('''
        INSERT INTO user_scores (user_id, username, first_name, score, game_time, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, score, game_time, datetime.now()))
    
    # Обновляем таблицу лучших результатов
    cursor.execute('''
        INSERT OR REPLACE INTO user_best_scores (user_id, username, first_name, best_score, games_played, last_played)
        VALUES (
            ?,
            ?,
            ?,
            COALESCE((SELECT MAX(score) FROM user_scores WHERE user_id = ?), ?),
            COALESCE((SELECT COUNT(*) FROM user_scores WHERE user_id = ?), 0) + 1,
            ?
        )
    ''', (user_id, username, first_name, user_id, score, user_id, datetime.now()))
    
    conn.commit()
    conn.close()
    logger.info(f"Сохранен результат для user_id={user_id}: {score} очков")

def get_top_scores(limit=10):
    """Возвращает топ-N результатов всех игроков"""
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    
    # Получаем лучшие результаты каждого пользователя
    cursor.execute('''
        SELECT DISTINCT 
            user_id, 
            username, 
            first_name, 
            MAX(score) as best_score
        FROM user_scores 
        GROUP BY user_id
        ORDER BY best_score DESC 
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_user_stats(user_id):
    """Возвращает статистику пользователя"""
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            MAX(score) as best_score,
            COUNT(*) as total_games,
            AVG(score) as avg_score,
            MIN(created_at) as first_game,
            MAX(created_at) as last_game
        FROM user_scores 
        WHERE user_id = ?
    ''', (user_id,))
    
    stats = cursor.fetchone()
    conn.close()
    
    if stats and stats[0]:
        return {
            'best_score': stats[0],
            'total_games': stats[1],
            'avg_score': round(stats[2], 1) if stats[2] else 0,
            'first_game': stats[3],
            'last_game': stats[4]
        }
    return None

def get_recent_games(limit=20):
    """Возвращает последние игры"""
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, first_name, score, created_at 
        FROM user_scores 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results

# ===== ОБРАБОТЧИКИ КОМАНД БОТА =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - только приветствие"""
    welcome_text = (
        "🎮 <b>Добро пожаловать в 3-In-A-Row Game Bot!</b>\n\n"
        "Это игра в стиле \"три в ряд\" с системой рейтингов, аналогичной популярным играм в Telegram.\n\n"
        "<b>Доступные команды:</b>\n"
        "▫️ /game - Начать играть\n"
        "▫️ /top - Таблица рекордов\n"
        "▫️ /mystats - Моя статистика\n"
        "▫️ /recent - Последние игры\n\n"
        "После завершения игры ваш результат автоматически сохранится в таблице лидеров!"
    )
    
    # Добавляем кнопки для быстрого доступа
    keyboard = [
        [InlineKeyboardButton("🎮 Начать игру", callback_data="start_game")],
        [InlineKeyboardButton("🏆 Таблица лидеров", callback_data="show_top")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)
    logger.info(f"Пользователь {update.effective_user.id} использовал команду /start")

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /game - отправляет игру"""
    # Отправляем игру без дополнительных кнопок
    await update.message.reply_game(game_short_name=GAME_SHORT_NAME)
    logger.info(f"Пользователь {update.effective_user.id} запросил игру")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает таблицу рекордов"""
    top_scores = get_top_scores(10)
    
    if not top_scores:
        await update.message.reply_text("🏆 Таблица рекордов пока пуста. Будьте первым!")
        return
    
    lines = ["🏆 <b>Топ-10 игроков:</b>\n"]
    for i, (user_id, username, first_name, score) in enumerate(top_scores, 1):
        # Формируем имя для отображения
        if first_name:
            display_name = first_name
            if username:
                display_name = f"{first_name} (@{username})"
        elif username:
            display_name = f"@{username}"
        else:
            display_name = f"Игрок #{user_id}"
        
        # Добавляем медали для первых трех мест
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        
        lines.append(f"{medal}{i}. {display_name}: <b>{score}</b>")
    
    # Добавляем информацию об общем количестве игроков
    conn = sqlite3.connect('game_leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM user_scores')
    total_players = cursor.fetchone()[0] or 0
    conn.close()
    
    lines.append(f"\n<b>Всего игроков:</b> {total_players}")
    
    await update.message.reply_html("\n".join(lines))
    logger.info(f"Пользователь {update.effective_user.id} запросил таблицу рекордов")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику пользователя"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    if not stats:
        await update.message.reply_text(
            "У вас пока нет сохраненных результатов.\n"
            "Сыграйте в игру через команду /game!"
        )
        return
    
    user = update.effective_user
    display_name = user.first_name or user.username or f"Игрок #{user_id}"
    
    stats_text = (
        f"📊 <b>Статистика {display_name}:</b>\n\n"
        f"🏆 <b>Лучший результат:</b> {stats['best_score']}\n"
        f"🎮 <b>Всего игр:</b> {stats['total_games']}\n"
        f"📈 <b>Средний результат:</b> {stats['avg_score']}\n"
        f"⏰ <b>Первая игра:</b> {stats['first_game'][:10] if stats['first_game'] else 'Нет данных'}\n"
        f"🕐 <b>Последняя игра:</b> {stats['last_game'][:10] if stats['last_game'] else 'Нет данных'}"
    )
    
    await update.message.reply_html(stats_text)
    logger.info(f"Пользователь {user_id} запросил свою статистику")

async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает последние игры"""
    recent_games = get_recent_games(15)
    
    if not recent_games:
        await update.message.reply_text("Пока нет сохраненных игр.")
        return
    
    lines = ["🕐 <b>Последние игры:</b>\n"]
    
    for username, first_name, score, game_time in recent_games:
        # Формируем имя для отображения
        if first_name:
            display_name = first_name
        elif username:
            display_name = f"@{username}"
        else:
            display_name = "Аноним"
        
        # Форматируем время
        time_str = game_time[:16] if game_time else "неизвестно"
        
        lines.append(f"• {display_name}: <b>{score}</b> ({time_str})")
    
    await update.message.reply_html("\n".join(lines))
    logger.info(f"Пользователь {update.effective_user.id} запросил список последних игр")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам"""
    help_text = (
        "📋 <b>Список доступных команд:</b>\n\n"
        "▫️ /start - Начало работы с ботом\n"
        "▫️ /game - Начать играть в 3-In-A-Row\n"
        "▫️ /top - Показать таблицу рекордов\n"
        "▫️ /mystats - Показать вашу статистику\n"
        "▫️ /recent - Показать последние игры\n"
        "▫️ /help - Показать эту справку\n\n"
        "<b>Как играть:</b>\n"
        "1. Нажмите /game для запуска игры\n"
        "2. Игра откроется прямо в Telegram\n"
        "3. После завершения результат сохранится автоматически\n"
        "4. Проверьте свой рейтинг в таблице лидеров!\n\n"
        "<b>GitHub проекта:</b>\n"
        "https://github.com/arsmitt/3-in-a-row"
    )
    await update.message.reply_html(help_text)

# ===== ОБРАБОТЧИК CALLBACK-ЗАПРОСОВ =====
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
                
                # Получаем время игры, если оно есть
                game_time = game_data.get('time')
                
                logger.info(f"Получен результат от {user.id} ({user.first_name}): {score} очков")
                
                # === СОХРАНЯЕМ В НАШУ БАЗУ ДАННЫХ ===
                save_score_to_db(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    score=score,
                    game_time=game_time
                )
                
                # === ОПЦИОНАЛЬНО: сохраняем в Telegram API ===
                # Раскомментируйте, если хотите также использовать встроенные рекорды Telegram
                # try:
                #     await context.bot.set_game_score(
                #         user_id=user.id,
                #         score=score,
                #         chat_id=chat_id,
                #         message_id=message_id,
                #         force=True,
                #         disable_edit_message=True
                #     )
                # except Exception as e:
                #     logger.warning(f"Не удалось сохранить в таблицу Telegram: {e}")
                
                # Формируем ответ с информацией о результате
                user_stats = get_user_stats(user.id)
                reply_text = f"✅ <b>Результат сохранен!</b>\n\n"
                reply_text += f"🏆 <b>Ваш счет:</b> {score}\n"
                
                if user_stats:
                    if score > user_stats['best_score']:
                        reply_text += "🎉 <b>Новый рекорд!</b>\n"
                    elif score == user_stats['best_score']:
                        reply_text += "👍 Повторили свой рекорд!\n"
                    
                    reply_text += f"📊 <b>Ваш лучший результат:</b> {user_stats['best_score']}\n"
                    reply_text += f"🎮 <b>Всего игр:</b> {user_stats['total_games']}"
                
                # Получаем текущий топ для сравнения
                top_scores = get_top_scores(3)
                if top_scores:
                    reply_text += "\n\n🏆 <b>Текущие лидеры:</b>\n"
                    for i, (_, _, fname, top_score) in enumerate(top_scores[:3], 1):
                        name = fname or f"Игрок {i}"
                        medal = "🥇" if i == 1 else ("🥈" if i == 2 else "🥉")
                        reply_text += f"{medal} {name}: {top_score}\n"
                    
                    # Проверяем, вошел ли пользователь в топ
                    user_position = None
                    all_scores = get_top_scores(100)  # Получаем больше позиций для поиска
                    for pos, (uid, _, _, _) in enumerate(all_scores, 1):
                        if uid == user.id:
                            user_position = pos
                            break
                    
                    if user_position:
                        reply_text += f"\n<b>Ваша позиция в рейтинге:</b> #{user_position}"
                
                await query.answer(reply_text, show_alert=True)
                return
                
        except json.JSONDecodeError:
            # Если не JSON, обрабатываем как обычный callback_data
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
    
    # 3. Обработка кнопок из меню
    await query.answer()
    
    if query.data == "start_game":
        await query.message.reply_game(game_short_name=GAME_SHORT_NAME)
        
    elif query.data == "show_top":
        # Показываем таблицу лидеров
        top_scores = get_top_scores(10)
        
        if not top_scores:
            await query.message.reply_text("🏆 Таблица рекордов пока пуста. Будьте первым!")
            return
        
        lines = ["🏆 <b>Топ-10 игроков:</b>\n"]
        for i, (user_id, username, first_name, score) in enumerate(top_scores, 1):
            if first_name:
                display_name = first_name
            elif username:
                display_name = f"@{username}"
            else:
                display_name = f"Игрок #{user_id}"
            
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            lines.append(f"{medal}{i}. {display_name}: <b>{score}</b>")
        
        await query.message.reply_html("\n".join(lines))
        
    elif query.data == "my_stats":
        # Показываем статистику пользователя
        user_id = query.from_user.id
        stats = get_user_stats(user_id)
        
        if not stats:
            await query.message.reply_text(
                "У вас пока нет сохраненных результатов.\n"
                "Сыграйте в игру через кнопку '🎮 Начать игру'!"
            )
            return
        
        user = query.from_user
        display_name = user.first_name or user.username or f"Игрок #{user_id}"
        
        stats_text = (
            f"📊 <b>Статистика {display_name}:</b>\n\n"
            f"🏆 <b>Лучший результат:</b> {stats['best_score']}\n"
            f"🎮 <b>Всего игр:</b> {stats['total_games']}\n"
            f"📈 <b>Средний результат:</b> {stats['avg_score']}"
        )
        
        await query.message.reply_html(stats_text)

# ===== ЗАПУСК БОТА =====
def main() -> None:
    """Основная функция запуска бота"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("recent", recent_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик всех callback-запросов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("Бот запущен с системой рейтингов!")
    logger.info("Доступные команды: /start, /game, /top, /mystats, /recent, /help")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
