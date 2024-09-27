import os
import telebot
import sqlite3
from telebot import types
from dotenv import load_dotenv

load_dotenv()

bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))

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

def save_request(user_id, user_message):
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_requests (user_id, user_message) VALUES (?, ?)", (user_id, user_message))
    conn.commit()
    conn.close()

def save_reply(request_id, admin_reply):
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE user_requests SET admin_reply = ? WHERE id = ?", (admin_reply, request_id))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Частые вопросы')
    itembtn2 = types.KeyboardButton('Помощь')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, "Привет! Чем могу помочь?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Частые вопросы")
def show_frequent_questions(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Кнопка 1')
    itembtn2 = types.KeyboardButton('Кнопка 2')
    back_button = types.KeyboardButton('Назад')
    markup.add(itembtn1, itembtn2, back_button)
    bot.send_message(message.chat.id, "Выберите вопрос:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Помощь")
def help_request(message):
    msg = bot.send_message(message.chat.id, "Пожалуйста, опишите ваш вопрос. Администратор получит ваше сообщение.")
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    user_id = message.chat.id
    user_message = message.text
    save_request(user_id, user_message)
    bot.send_message(ADMIN_CHAT_ID, f"Сообщение от пользователя {user_id}:\n{user_message}")
    bot.send_message(user_id, "Ваше сообщение отправлено администратору.")

@bot.message_handler(func=lambda message: message.text == "Назад")
def go_back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Частые вопросы')
    itembtn2 = types.KeyboardButton('Помощь')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=markup)

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
    user_id = cursor.fetchone()[0]
    conn.close()

    bot.send_message(user_id, f"Ответ от администратора: {admin_reply}")
    bot.send_message(message.chat.id, "Сообщение отправлено пользователю.")

if __name__ == '__main__':
    init_db()
    bot.polling(none_stop=True)
