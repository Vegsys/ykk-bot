# === ✅ YKK Shop Bot (FIXED: Redis State) ===
# Автор: @Vegsys | Telegram бот для YKK Shop 🇯🇵
# Версия: 2025.12 | Webhook + threading + ручной маршрутизатор + ForceReply + Redis

import os
import telebot
from telebot import types
from datetime import datetime
from flask import Flask, request
import threading
import redis # <-- 1. Импортируем Redis

# === 1. Настройки и инициализация ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))
# --- НОВОЕ: Подключение к Redis ---
REDIS_URL = os.getenv("REDIS_URL") # Render предоставит эту переменную

if not TOKEN:
    raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_BOT_TOKEN не задан!")
if not ADMIN_ID:
    print("⚠️ ПРЕДУПРЕЖДЕНИЕ: TELEGRAM_ADMIN_ID не задан.")
if not REDIS_URL:
    raise ValueError("❌ КРИТИЧЕСКАЯ ОШИБКА: REDIS_URL не задан! (Нужно добавить Add-on на Render)")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- НОВОЕ: Инициализация клиента Redis ---
try:
    # <--- 2. Создаем клиент Redis, который будет общим для всех воркеров
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping() # Проверяем соединение
    print("✅ Успешное подключение к Redis.")
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к Redis! {e}")
    redis_client = None # Продолжаем работу, но заказы не будут сохраняться

# === 2. Установка webhook ===
bot.remove_webhook()
if WEBHOOK_URL:
    full_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
    try:
        bot.set_webhook(url=full_url)
        print(f"🌐 Webhook установлен: {full_url}")
    except Exception as e:
        print(f"❌ Ошибка установки Webhook: {e}")
else:
    print("⚠️ Переменная RENDER_EXTERNAL_URL не указана!")


# === 3. Основная логика ===

def greeting():
    """Приветствие по времени суток."""
    hour = datetime.now().hour
    if 5 <= hour < 12: return "Доброе утро 🌅"
    elif 12 <= hour < 17: return "Добрый день ☀️"
    elif 17 <= hour < 23: return "Добрый вечер 🌇"
    else: return "Доброй ночи 🌙"


def main_menu():
    """Главное меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📘 Каталог", "🛒 Сделать заказ")
    return markup


def start(message):
    """Ответ на команду /start."""
    print(f"[{datetime.now()}] ▶️ /start от {message.chat.id}")
    name = message.from_user.first_name or ""
    bot.send_message(
        message.chat.id,
        f"{greeting()}, *{name}!* 👋\n\n"
        f"Добро пожаловать в *YKK Shop* — официальный бот легендарных молний *YKK* 🇯🇵\n\n"
        f"🔹 Здесь вы можете:\n"
        f"— Посмотреть каталог (PDF)\n"
        f"— Оформить оптовый заказ\n\n",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


def catalog(message):
    """Отправка ссылки на каталог."""
    print(f"[{datetime.now()}] ▶️ Каталог для {message.chat.id}")
    bot.send_message(
        message.chat.id,
        "📎 Наш каталог YKK (PDF):\n"
        "[Скачать каталог](https://disk.yandex.ru/i/ytpOf5X_TUNBBw)",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


def order(message):
    """Запуск оформления заказа (ForceReply)."""
    print(f"[{datetime.now()}] ▶️ Начало заказа для {message.chat.id}")
    markup = types.ForceReply(selective=True, input_field_placeholder="Напишите детали заказа...")
    bot.send_message(message.chat.id, "🧵 Введите детали заказа (тип молнии, длина, количество):", reply_markup=markup)


def handle_order(message):
    """Шаг 2: Принимаем заказ и запрашиваем телефон."""
    print(f"[{datetime.now()}] 💬 Получен заказ от {message.chat.id}")
    order_text = message.text.strip()
    if not order_text:
        bot.send_message(message.chat.id, "Пожалуйста, введите детали заказа.")
        return

    # --- ИЗМЕНЕНО: Сохраняем текст заказа в Redis ---
    # <--- 3. Вместо user_orders[...], используем redis_client.set()
    try:
        if redis_client:
            # Ключ будет 'order:USER_ID', значение - текст заказа, 
            # храним 1 час (3600 секунд)
            redis_client.set(f"order:{message.chat.id}", order_text, ex=3600)
        else:
            raise Exception("Redis client не инициализирован.")
            
    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: Не удалось сохранить заказ в Redis! {e}")
        bot.send_message(message.chat.id, "Ой, произошла внутренняя ошибка. Попробуйте 'Сделать заказ' еще раз.")
        return

    # Запрашиваем телефон
    markup = types.ForceReply(selective=True, input_field_placeholder="Введите номер телефона...")
    bot.send_message(
        message.chat.id,
        "📞 Укажите, пожалуйста, контактный номер телефона для связи:",
        reply_markup=markup
    )


def handle_phone(message):
    """Шаг 3: Приём телефона, подтверждение и уведомление админа."""
    print(f"[{datetime.now()}] 📞 Телефон от {message.chat.id}")

    phone = message.text.strip()
    if not phone or len(phone) < 5:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер телефона.")
        return

    # --- ИЗМЕНЕНО: Забираем заказ из Redis ---
    # <--- 4. Вместо user_orders.pop(), используем redis_client.getdel()
    order_text = "—" # Значение по умолчанию
    try:
        if redis_client:
            # getdel = получить значение и сразу удалить его
            key = f"order:{message.chat.id}"
            order_data = redis_client.getdel(key)
            if order_data:
                order_text = order_data.decode('utf-8') # Redis возвращает байты, декодируем в строку
            else:
                 print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Заказ для {message.chat.id} не найден в Redis (возможно, истек).")
        else:
            raise Exception("Redis client не инициализирован.")
            
    except Exception as e:
        print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить заказ из Redis! {e}")
        bot.send_message(message.chat.id, "Ой, произошла ошибка. Не удалось найти ваш заказ. Пожалуйста, начните сначала.")
        return

    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Ваш заказ и контакт приняты.\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=main_menu(),
    )

    try:
        if ADMIN_ID:
            bot.send_message(
                ADMIN_ID,
                f"📦 *Новый заказ YKK!*\n\n"
                f"👤 От: @{message.from_user.username or 'Без username'}\n"
                f"🧾 Имя: {message.from_user.first_name}\n"
                f"💬 Заказ: {order_text}\n"
                f"📞 Телефон: {phone}",
                parse_mode="Markdown",
            )
    except Exception as e:
        print(f"[Ошибка отправки админу {ADMIN_ID}]: {e}")


# --- УДАЛЕНО: Временное хранилище (user_orders = {}) больше не нужно ---


# === 4. Ручной маршрутизатор (асинхронная обработка) ===
def _process_update(update):
    """Ручная маршрутизация сообщений (поддержка ForceReply)."""
    if not update or not update.message:
        return

    try:
        message = update.message
        text = message.text or ""
        print(f"[{datetime.now()}] 🔹 Update: '{text}' от {message.chat.id}")

        # Ответ на запрос телефона
        if message.reply_to_message and message.reply_to_message.text.startswith("📞 Укажите"):
            handle_phone(message)
            return

        # Ответ на запрос деталей заказа
        if message.reply_to_message and message.reply_to_message.text.startswith("🧵 Введите детали заказа"):
            handle_order(message)
            return

        # Обычные команды
        if text.startswith("/start"):
            start(message)
        elif text == "📘 Каталог":
            catalog(message)
        elif text == "🛒 Сделать заказ":
            order(message)
        else:
            bot.send_message(
                message.chat.id,
                "🙌 Для навигации используйте меню ниже.",
                reply_markup=main_menu(),
            )

    except Exception as e:
        print(f"🚨 Ошибка в _process_update: {e}")


# === 5. Flask Webhook ===
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Webhook — обработка входящих апдейтов от Telegram."""
    try:
        json_data = request.get_json(silent=True)
        if not json_data:
            return "Invalid JSON", 400

        update = telebot.types.Update.de_json(json_data)
        threading.Thread(target=_process_update, args=(update,)).start()
        return "OK", 200
    except Exception as e:
        print(f"🚨 Ошибка во Flask webhook: {e}")
        return "Error", 500


@app.route("/", methods=["GET"])
def index():
    return "✅ YKK Shop Bot стабильно работает 2025 на Render!", 200


# === 6. Запуск (локальный режим не используется) ===
if __name__ == "__main__":
    print("⚠️ Этот бот работает только через Webhook (Render).")
    print("Используйте polling-версию для локальных тестов.")