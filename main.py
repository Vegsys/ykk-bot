# === ✅ YKK Shop Bot (Render-ready, STABLE Webhook) ===
# Автор: @Vegsys | Telegram бот для YKK Shop 🇯🇵
# ФИНАЛЬНАЯ ВЕРСИЯ: Использует threading (асинхронность) + РУЧНОЙ 
# МАРШРУТИЗАТОР для 100% гарантии ответа.

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
# ВАЖНО: Мы больше не используем декораторы @bot.message_handler
# Мы будем вызывать эти функции вручную из _process_update

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
    """Начало процесса оформления заказа."""
    print(f"✅ [Поток] РУЧНОЙ ВЫЗОВ: 'Сделать заказ' для чата ID: {message.chat.id}")
    msg = bot.send_message(
        message.chat.id,
        "🧵 Введите детали заказа (тип молнии, длина, количество):",
    )
    # register_next_step_handler - это единственный обработчик, 
    # который мы оставляем, так как он работает иначе.
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

# --- ФУНКЦИЯ ДЛЯ АСИНХРОННОЙ ОБРАБОТКИ (НОВЫЙ РУЧНОЙ РЕЖИМ) ---
def _process_update(update):
    """
    РУЧНОЙ МАРШРУТИЗАТОР.
    Мы больше не используем bot.process_new_updates().
    Мы сами проверяем сообщение и вызываем нужную функцию.
    """
    if not update or not update.message or not update.message.text:
        print("✔️ [Поток] Получен пустой или нетекстовый update, игнорируем.")
        return

    try:
        message = update.message
        text = message.text
        
        print(f"✔️ [Поток] Update {update.update_id} принят в обработку. Текст: '{text}'")

        # --- НАШ РУЧНОЙ МАРШРУТИЗАТОР ---
        if text.startswith("/start"):
            start(message)
        elif text == "📘 Каталог":
            catalog(message)
        elif text == "🛒 Сделать заказ":
            order(message)
        else:
            # Обработка для register_next_step_handler
            # Эта часть нужна, чтобы "Сделать заказ" поймал ответ.
            if bot.reply_handlers:
                print(f"✔️ [Поток] Передача сообщения в reply_handler (для 'Сделать заказ')")
                bot.process_new_messages([message])
            else:
                print(f"⚠️ [Поток] Неизвестная команда: '{text}'")
                # Можно отправить сообщение по умолчанию, если нужно
                # bot.send_message(message.chat.id, "Неизвестная команда.")

    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА в асинхронном потоке (_process_update): {e}")


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
    print("Для локальной разработки этот код должен использовать polling.")
    print("Удаляю вебхук и запускаю polling...")
    bot.remove_webhook()
    # ВАЖНО: для локального запуска polling, нам нужно
    # вернуть старые декораторы @bot.message_handler!
    # Этот код предназначен ТОЛЬКО для Render (Webhook).
    # Для локальной отладки используйте предыдущую версию с polling.
    
    print("Ошибка: Этот код (с ручным роутером) предназначен только для Webhook.")
    print("Для локального запуска (polling) используйте версию с @bot.message_handler.")