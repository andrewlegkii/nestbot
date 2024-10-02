import os
import telebot
import sqlite3
from telebot import types
from dotenv import load_dotenv

load_dotenv()

bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            admin_reply TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    """)
    conn.commit()
    conn.close()

# Функция для сохранения запроса пользователя
def save_request(user_id, user_message):
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_requests (user_id, user_message) VALUES (?, ?)", (user_id, user_message))
    request_id = cursor.lastrowid  # Получаем ID запроса
    conn.commit()
    conn.close()
    return request_id

# Функция для сохранения ответа администратора
def save_reply(request_id, admin_reply):
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE user_requests SET admin_reply = ? WHERE id = ?", (admin_reply, request_id))
    conn.commit()
    conn.close()

# Команда для старта бота
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Частые вопросы')
    itembtn2 = types.KeyboardButton('Помощь')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, "Привет! Чем могу помочь?", reply_markup=markup)

# Частые вопросы
@bot.message_handler(func=lambda message: message.text == "Частые вопросы")
def show_frequent_questions(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Какой пакет документов?')
    itembtn2 = types.KeyboardButton('Где найти накладную на паллеты?')
    back_button = types.KeyboardButton('Назад')
    markup.add(itembtn1, itembtn2, back_button)
    bot.send_message(message.chat.id, "Выберите вопрос:", reply_markup=markup)

# Обработка запроса "Помощь"
@bot.message_handler(func=lambda message: message.text == "Помощь")
def help_request(message):
    msg = bot.send_message(message.chat.id, "Пожалуйста, опишите ваш вопрос. Администратор получит ваше сообщение.")
    bot.register_next_step_handler(msg, forward_to_admin)

# Передача сообщения администратору и сохранение запроса
def forward_to_admin(message):
    user_id = message.chat.id
    user_message = message.text

    # Сохранение запроса пользователя
    request_id = save_request(user_id, user_message)

    # Отправляем ID запроса пользователю
    bot.send_message(user_id, f"Ваш запрос зарегистрирован под номером: {request_id}. Ожидайте ответа.")

    # Отправляем сообщение администратору с ID запроса
    bot.send_message(ADMIN_CHAT_ID, f"Запрос от пользователя {user_id} (ID запроса: {request_id}):\n{user_message}")

# Кнопка "Назад" возвращает в главное меню
@bot.message_handler(func=lambda message: message.text == "Назад")
def go_back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Частые вопросы')
    itembtn2 = types.KeyboardButton('Помощь')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)

# Команда для администратора для ответа пользователю
@bot.message_handler(commands=['reply'])
def reply_to_user(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.send_message(message.chat.id, "Команда доступна только администратору.")
        return

    parts = message.text.split(' ', 2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Использование: /reply <id запроса> <сообщение>")
        return

    request_id = int(parts[1])
    admin_reply = parts[2]
    save_reply(request_id, admin_reply)

    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM user_requests WHERE id = ?", (request_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        bot.send_message(message.chat.id, f"Запрос с ID {request_id} не найден.")
    else:
        user_id = result[0]
        bot.send_message(user_id, f"Администратор ответил на ваш запрос (ID {request_id}):\n{admin_reply}")
        bot.send_message(message.chat.id, f"Ответ отправлен пользователю {user_id}.")

# Инициализация базы данных при запуске
init_db()

# Запуск бота
bot.polling(none_stop=True)
