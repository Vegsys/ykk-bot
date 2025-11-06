# === ✅ YKK Shop Bot (Render-ready, STABLE Webhook) ===
# Автор: @Vegsys | Telegram бот для YKK Shop 🇯🇵
# ФИНАЛЬНАЯ ВЕРСИЯ: Использует threading (асинхронность) + РУЧНОЙ 
# МАРШРУТИЗАТОР + ForceReply для 100% гарантии ответа.

import os
import telebot
from telebot import types
from datetime import datetime
from flask import Flask, request
import json 
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

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# === 2. ОБЯЗАТЕЛЬНАЯ УСТАНОВКА WEBHOOK ===
bot.remove_webhook()
if WEBHOOK_URL:
    full_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
    try:
        bot.set_webhook(url=full_url)
        print(f"🌐 Webhook успешно установлен: {full_url}")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось установить Webhook! Ошибка: {e}")
else:
    print("⚠️ Переменная RENDER_EXTERNAL_URL не указана!")


# === 3. Логика Бота (Обработчики) ===

def greeting():
    """Приветствие в зависимости от времени суток."""
    hour = datetime.now().hour
    if 5 <= hour < 12: return "Доброе утро 🌅"
    elif 12 <= hour < 17: return "Добрый день ☀️"
    elif 17 <= hour < 23: return "Добрый вечер 🌇"
    else: return "Доброй ночи 🌙"

def main_menu():
    """Создание клавиатуры главного меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📘 Каталог", "🛒 Сделать заказ")
    return markup

def start(message):
    """Обработчик команды /start."""
    print(f"✅ [Поток] РУЧНОЙ ВЫЗОВ: /start для чата ID: {message.chat.id}")
    
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

def catalog(message):
    """Обработчик кнопки Каталог."""
    print(f"✅ [Поток] РУЧНОЙ ВЫЗОВ: 'Каталог' для чата ID: {message.chat.id}")
    bot.send_message(
        message.chat.id,
        "📎 Наш каталог YKK (PDF):\n"
        "[Скачать каталог](https://disk.yandex.ru/i/ytpOf5X_TUNBBw)",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

def order(message):
    """
    Начало процесса оформления заказа. 
    ИСПОЛЬЗУЕМ ForceReply ВМЕСТО register_next_step_handler.
    """
    print(f"✅ [Поток] РУЧНОЙ ВЫЗОВ: 'Сделать заказ' для чата ID: {message.chat.id}")
    
    # Создаем markup, который заставит пользователя ответить на это сообщение
    markup = types.ForceReply(
        selective=True,  # Только для этого пользователя
        input_field_placeholder="Напишите здесь детали заказа..."
    )
    
    bot.send_message(
        message.chat.id,
        "🧵 Введите детали заказа (тип молнии, длина, количество):",
        reply_markup=markup
    )
    # Мы больше НЕ ИСПОЛЬЗУЕМ register_next_step_handler

def handle_order(message):
    """
    Обработка текста заказа и отправка админу.
    Эта функция теперь вызывается вручную из _process_update.
    """
    print(f"✅ [Поток] РУЧНОЙ ВЫЗОВ: handle_order для чата ID: {message.chat.id}")
    order_text = message.text.strip()
    if not order_text:
        bot.send_message(message.chat.id, "Пожалуйста, введите детали заказа.")
        return

    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Ваш заказ принят.\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=main_menu(),
    )

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

# --- ФУНКЦИЯ ДЛЯ АСИНХРОННОЙ ОБРАБОТКИ (РУЧНОЙ МАРШРУТИЗАТОР) ---
def _process_update(update):
    """
    РУЧНОЙ МАРШРУТИЗАТОР.
    Мы сами проверяем сообщение и вызываем нужную функцию.
    """
    if not update or not update.message:
        print("✔️ [Поток] Получен пустой update, игнорируем.")
        return

    try:
        message = update.message
        
        # --- НОВАЯ ПРОВЕРКА ДЛЯ ForceReply ---
        # Проверяем, является ли это сообщение ответом на наш запрос "Введите детали заказа"
        if message.reply_to_message and message.reply_to_message.text.startswith("🧵 Введите детали заказа"):
            handle_order(message)
            return # Заказ обработан, выходим
        # --- КОНЕЦ НОВОЙ ПРОВЕРКИ ---

        # Если это не ответ на заказ, продолжаем обычную маршрутизацию
        text = message.text
        if not text:
             print("✔️ [Поток] Получен нетекстовый update (стикер?), игнорируем.")
             return
        
        print(f"✔️ [Поток] Update {update.update_id} принят в обработку. Текст: '{text}'")

        # --- НАШ РУЧНОЙ МАРШРУТИЗАТОР ---
        if text.startswith("/start"):
            start(message)
        elif text == "📘 Каталог":
            catalog(message)
        elif text == "🛒 Сделать заказ":
            order(message)
        else:
            print(f"⚠️ [Поток] Неизвестная команда или обычный текст: '{text}'")
            # Можно отправить сообщение по умолчанию, если нужно
            # bot.send_message(message.chat.id, "Неизвестная команда.", reply_markup=main_menu())

    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА в асинхронном потоке (_process_update): {e}")


# === 4. Webhook и Flask-роуты ===
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
            raw_data = request.stream.read().decode("utf-8")
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА JSON. RAW Data: {raw_data[:200]}...")
            return "Invalid JSON", 400

        update = telebot.types.Update.de_json(json_data)
        
        # Запускаем наш НОВЫЙ ручной обработчик в отдельном потоке
        threading.Thread(target=_process_update, args=(update,)).start()
        
        # Немедленно возвращаем "OK" (200)
        return "OK", 200

    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА во Flask Webhook-роуте: {e}")
        return "Error", 500

@app.route("/", methods=["GET"])
def index():
    """Стартовая страница для проверки работоспособности сервера."""
    return "✅ YKK Shop Bot стабильно работает 2025 на Render!", 200


# === 5. Запуск для локальной разработки ===
if __name__ == "__main__":
    print("--- ВНИМАНИЕ: ЛОКАЛЬНЫЙ ЗАПУСК ---")
    print("Ошибка: Этот код (с ручным роутером) предназначен только для Webhook.")
    print("Для локального запуска (polling) используйте версию с @bot.message_handler.")