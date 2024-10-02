import os
import telebot
import sqlite3
from telebot import types
from dotenv import load_dotenv

load_dotenv()

bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID'))
DB_PASSWORD = os.getenv('DB_PASSWORD')

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
    # Добавляем ответы на частые вопросы в базу данных
    cursor.execute("INSERT INTO faq (question, answer) VALUES ('Какой пакет документов?', 'Для отгрузки товаров вам понадобятся накладная, товарный чек и сертификаты соответствия.')")
    cursor.execute("INSERT INTO faq (question, answer) VALUES ('Где найти накладную на паллеты?', 'Накладная обычно находится в вашей учетной системе или может быть запрошена у вашего менеджера.')")
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

# Функция для скачивания базы данных
def download_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Получаем все данные из таблицы user_requests
    cursor.execute("SELECT * FROM user_requests")
    user_requests_data = cursor.fetchall()

    # Получаем все данные из таблицы faq
    cursor.execute("SELECT * FROM faq")
    faq_data = cursor.fetchall()

    conn.close()

    # Записываем данные в текстовые файлы
    with open(f"{db_name.split('.')[0]}_requests.txt", "w", encoding="utf-8") as f:
        for row in user_requests_data:
            f.write(f"{row}\n")

    with open(f"{db_name.split('.')[0]}_faq.txt", "w", encoding="utf-8") as f:
        for row in faq_data:
            f.write(f"{row}\n")

    return f"{db_name.split('.')[0]}_requests.txt", f"{db_name.split('.')[0]}_faq.txt"

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

# Ответ на частый вопрос
@bot.message_handler(func=lambda message: message.text in ['Какой пакет документов?', 'Где найти накладную на паллеты?'])
def answer_faq(message):
    question = message.text
    conn = sqlite3.connect('nestle_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM faq WHERE question = ?", (question,))
    answer = cursor.fetchone()
    conn.close()

    if answer:
        bot.send_message(message.chat.id, answer[0])
    else:
        bot.send_message(message.chat.id, "Ответ на этот вопрос отсутствует.")

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

# Команда для скачивания баз данных
@bot.message_handler(commands=['data'])
def download_data(message):
    if message.chat.id != ADMIN_CHAT_ID:
        bot.send_message(message.chat.id, "Команда доступна только администратору.")
        return

    parts = message.text.split(' ')
    if len(parts) != 2 or parts[1] != DB_PASSWORD:
        bot.send_message(message.chat.id, "Неверный пароль. Попробуйте еще раз.")
        return

    # Скачивание баз данных
    user_requests_file, faq_file = download_db('nestle_bot.db')

    # Отправляем файлы администратору
    with open(user_requests_file, 'rb') as f:
        bot.send_document(ADMIN_CHAT_ID, f)
    with open(faq_file, 'rb') as f:
        bot.send_document(ADMIN_CHAT_ID, f)

    # Уведомление об успешной отправке
    bot.send_message(ADMIN_CHAT_ID, "Базы данных успешно скачаны.")

# Инициализация базы данных при запуске
init_db()

# Запуск бота
bot.polling(none_stop=True)
