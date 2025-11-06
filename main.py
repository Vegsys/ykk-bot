# === ✅ YKK Shop Bot (Render-ready, stable 2025) ===
# Автор: @Vegsys | Telegram бот для YKK Shop 🇯🇵

import os
import telebot
from telebot import types
from datetime import datetime
from flask import Flask, request
import asyncio 
import json # Добавлен для удобства работы с JSON-строками в Python

# === 1. Настройки и Инициализация ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not ADMIN_ID:
    raise ValueError("❌ Ошибка: TELEGRAM_ADMIN_ID не задан!")
if not TOKEN:
    raise ValueError("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан!")

# Инициализация бота и Flask
bot = telebot.TeleBot(TOKEN, threaded=True)
app = Flask(__name__)


# === 2. ОБЯЗАТЕЛЬНАЯ УСТАНОВКА WEBHOOK (Вынесено из __main__!) ===
bot.remove_webhook()
if WEBHOOK_URL:
    full_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
    try:
        # Установка вебхука происходит при импорте файла Gunicorn'ом
        bot.set_webhook(url=full_url)
        print(f"🌐 Webhook успешно установлен: {full_url}")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось установить Webhook! Ошибка: {e}")

else:
    print("⚠️ Переменная RENDER_EXTERNAL_URL не указана! Бот не сможет принимать сообщения.")


# === 3. Логика Бота ===

def greeting():
    """Приветствие в зависимости от времени суток."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро 🌅"
    elif 12 <= hour < 17:
        return "Добрый день ☀️"
    elif 17 <= hour < 23:
        return "Добрый вечер 🌇"
    else:
        return "Доброй ночи 🌙"

def main_menu():
    """Создание клавиатуры главного меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📘 Каталог", "🛒 Сделать заказ")
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    """Обработчик команды /start."""
    # Эту строку мы ждем в логах!
    print(f"✅ Получена команда /start от чата ID: {message.chat.id}")
    
    name = message.from_user.first_name or ""
    bot.send_message(
        message.chat.id,
        f"{greeting()}, *{name}!* 👋\n\n"
        f"Добро пожаловать в *YKK Shop* — бот легендарной *YKK* 🇯🇵\n\n"
        f"🔹 Здесь вы можете:\n"
        f"— Посмотреть каталог молний (PDF)\n"
        f"— Оформить оптовый заказ\n\n"
        f"Jamme — заряжай мечты ⚡️",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

@bot.message_handler(func=lambda msg: msg.text == "📘 Каталог")
def catalog(message):
    """Обработчик кнопки Каталог."""
    bot.send_message(
        message.chat.id,
        "📎 Наш каталог YKK (PDF):\n"
        "[Скачать каталог](https://disk.yandex.ru/i/ytpOf5X_TUNBBw)",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

@bot.message_handler(func=lambda msg: msg.text == "🛒 Сделать заказ")
def order(message):
    """Начало процесса оформления заказа."""
    msg = bot.send_message(
        message.chat.id,
        "🧵 Введите детали заказа (тип молнии, длина, количество):",
    )
    bot.register_next_step_handler(msg, handle_order)

def handle_order(message):
    """Обработка текста заказа и отправка админу."""
    order_text = message.text.strip()
    if not order_text:
        bot.send_message(message.chat.id, "Пожалуйста, введите детали заказа.")
        return

    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Ваш заказ принят.\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=main_menu(),
    )

    # Отправка админу
    try:
        bot.send_message(
            ADMIN_ID,
            f"📦 *Новый заказ!*\n\n"
            f"👤 От: @{message.from_user.username or 'Без username'}\n"
            f"🧾 Имя: {message.from_user.first_name}\n"
            f"💬 Заказ: {order_text}",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"[Ошибка отправки админу {ADMIN_ID}]: {e}")


# === 4. Webhook и Flask-роуты (Обновлено: Добавлено логгирование входящих данных) ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Основной роут, куда Telegram отправляет обновления."""
    try:
        # Читаем сырые данные из запроса
        data = request.stream.read().decode("utf-8")
        
        # <<< НОВАЯ КРИТИЧЕСКАЯ ОТЛАДОЧНАЯ СТРОКА >>>
        print(f"⬅️ Получен Webhook Update (RAW): {data}")
        # <<< НОВАЯ КРИТИЧЕСКАЯ ОТЛАДОЧНАЯ СТРОКА >>>

        if request.headers.get('content-type') == 'application/json':
            update = telebot.types.Update.de_json(data)
            bot.process_new_updates([update])
            return "OK", 200
        else:
            return "Content-Type must be application/json", 400
    except Exception as e:
        print(f"[Ошибка при обработке Webhook-запроса]: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    """Стартовая страница для проверки работоспособности сервера."""
    return "✅ YKK Shop Bot стабильно работает 24/7 на Render!", 200


# === 5. Запуск для локальной разработки ===
if __name__ == "__main__":
    print(f"🚀 Запуск Flask сервера для локальной отладки на порту {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)