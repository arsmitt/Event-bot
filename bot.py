import telebot
import os

# Получаем токен из переменной окружения (так безопаснее)
TOKEN = os.environ.get('BOT_TOKEN')  # Токен вы позже укажете в настройках Bothost
bot = telebot.TeleBot(TOKEN)

# --- Обработчики команд (остаются прежними) ---
@bot.message_handler(commands=['game'])
def send_game(message):
    bot.send_game(message.chat.id, "Event3IR")  # Убедись, что short_name точный!

@bot.callback_query_handler(func=lambda call: call.game_short_name == "Event3IR")
def game_query(call):
    # ВСТАВЬ СЮДА РЕАЛЬНЫЙ URL СВОЕЙ ИГРЫ!
    bot.answer_callback_query(call.id, url="https://github.com/arsmitt/3-in-a-row/blob/main/index.html")

# --- Ключевое изменение для Bothost: Вебхук ---
# Эта часть запускает веб-сервер, который слушает запросы от Telegram
if __name__ == '__main__':
    # Для локального тестирования можно оставить polling
    # bot.polling()
    # Но для деплоя на Bothost нужно использовать это:
    import flask
    from flask import request
    
    app = flask.Flask(__name__)
    
    @app.route('/', methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            flask.abort(403)
    
    # Запускаем Flask-сервер
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
