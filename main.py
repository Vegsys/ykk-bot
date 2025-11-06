# === ✅ YKK Shop Bot (Render-ready, STABLE Webhook) ===
# Автор: @Vegsys | Telegram бот для YKK Shop 🇯🇵
# ФИНАЛЬНАЯ ВЕРСИЯ: Использует threading для асинхронной обработки webhook,
# что решает проблему с таймаутами и блокировками на Render/Gunicorn.

import os
import telebot
from telebot import types
from datetime import datetime
from flask import Flask, request
import json
# КЛЮЧЕВОЙ МОДУЛЬ: threading для асинхронного выполнения задач
import threading

# === 1. Настройки и Инициализация ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TOKEN:
    raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_BOT_TOKEN не задан!")
if not ADMIN_ID:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: TELEGRAM_ADMIN_ID не задан. Заказы не будут отправляться админу.")


# Инициализация бота: Без threaded=True (это важно для вебхука)
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# === 2. ОБЯЗАТЕЛЬНАЯ УСТАНОВКА WEBHOOK ===
# Этот код выполняется ОДИН РАЗ при запуске сервера Gunicorn
bot.remove_webhook()
if WEBHOOK_URL:
    full_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
    try:
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
    print(f"✅ [Поток] Обработка /start для чата ID: {message.chat.id}")
    
    name = message.from_user.first_name or ""
    try:
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
        print(f"✔️ [Поток] Ответ на /start успешно отправлен в чат ID: {message.chat.id}")
    except Exception as e:
        print(f"🚨 [Поток] Ошибка при отправке ответа на /start в чат {message.chat.id}: {e}")


@bot.message_handler(func=lambda msg: msg.text == "📘 Каталог")
def catalog(message):
    """Обработчик кнопки Каталог."""
    print(f"✅ [Поток] Обработка 'Каталог' для чата ID: {message.chat.id}")
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
    print(f"✅ [Поток] Обработка 'Сделать заказ' для чата ID: {message.chat.id}")
    msg = bot.send_message(
        message.chat.id,
        "🧵 Введите детали заказа (тип молнии, длина, количество):",
    )
    bot.register_next_step_handler(msg, handle_order)

def handle_order(message):
    """Обработка текста заказа и отправка админу."""
    print(f"✅ [Поток] Обработка заказа (next_step) для чата ID: {message.chat.id}")
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
        if ADMIN_ID:
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

# --- ФУНКЦИЯ ДЛЯ АСИНХРОННОЙ ОБРАБОТКИ ---
def _process_update(update):
    """
    Эта функция запускается в отдельном потоке (Thread),
    чтобы не блокировать основной Gunicorn-воркер.
    """
    try:
        bot.process_new_updates([update])
        print(f"✔️ [Поток] Update {update.update_id} успешно обработан.")
    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА в асинхронном потоке: {e}")

# === 4. Webhook и Flask-роуты (РЕШЕНИЕ ПРОБЛЕМЫ) ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """
    Основной роут.
    1. Немедленно запускает новый поток (Thread) для обработки.
    2. Немедленно возвращает 200 OK, чтобы удовлетворить Telegram.
    """
    try:
        json_data = request.get_json(silent=True)
        
        if json_data is None:
            # Если JSON не удалось получить
            raw_data = request.stream.read().decode("utf-8")
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА JSON. RAW Data: {raw_data[:200]}...")
            return "Invalid JSON", 400

        # print(f"⬅️ [Сервер] Получен Webhook Update (JSON): {json_data}")

        update = telebot.types.Update.de_json(json_data)
        
        # !!! КЛЮЧЕВОЙ МОМЕНТ: Запускаем обработку в отдельном потоке !!!
        threading.Thread(target=_process_update, args=(update,)).start()
        
        # Немедленно возвращаем "OK" (200), не дожидаясь ответа бота
        return "OK", 200

    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА во Flask Webhook-роуте: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    """Стартовая страница для проверки работоспособности сервера."""
    return "✅ YKK Shop Bot стабильно работает 24/7 на Render!", 200


# === 5. Запуск для локальной разработки ===
if __name__ == "__main__":
    print(f"🚀 Запуск Flask сервера для локальной отладки на порту {PORT}")
    # При локальном запуске этот код НЕ будет работать,
    # так как Flask по умолчанию однопоточный.
    # Для локальной отладки используйте bot.polling().
    # app.run(host="0.0.0.0", port=PORT, debug=True)
    
    print("--- ВНИМАНИЕ: ЛОКАЛЬНЫЙ ЗАПУСК ---")
    print("Для локальной разработки используйте метод polling.")
    print("Удаляю вебхук и запускаю polling...")
    bot.remove_webhook()
    bot.polling(none_stop=True)