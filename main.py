# === YKK Shop Bot (Render-ready version) ===
# Автор: @Vegsys | 2025

import os
import telebot
from telebot import types
from datetime import datetime
from flask import Flask, request

# --- Настройки ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "0")
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

if not TOKEN:
    raise ValueError("Ошибка: TELEGRAM_BOT_TOKEN не задан!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Приветствие по времени ---
def greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро 🌅"
    elif 12 <= hour < 17:
        return "Добрый день ☀️"
    elif 17 <= hour < 23:
        return "Добрый вечер 🌇"
    else:
        return "Доброй ночи 🌙"

# --- Главное меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📘 Каталог", "🛒 Сделать заказ")
    return markup

# --- Команда /start ---
@bot.message_handler(commands=["start"])
def start(message):
    user_name = message.from_user.first_name or ""
    bot.send_message(
        message.chat.id,
        f"{greeting()}, *{user_name}!* 👋\n\n"
        f"Добро пожаловать в *YKK Shop* — бот легендарной *YKK* 🇯🇵\n\n"
        f"🔹 Здесь вы можете:\n"
        f"— Посмотреть каталог молний (PDF)\n"
        f"— Оформить оптовый заказ\n\n"
        f"Jamme — заряжай мечты ⚡️",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

# --- Каталог ---
@bot.message_handler(func=lambda msg: msg.text == "📘 Каталог")
def catalog(message):
    bot.send_message(
        message.chat.id,
        "📎 Наш каталог YKK (PDF):\n[Скачать каталог](https://disk.yandex.ru/i/ytpOf5X_TUNBBw)",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )

# --- Заказ ---
@bot.message_handler(func=lambda msg: msg.text == "🛒 Сделать заказ")
def order(message):
    msg = bot.send_message(
        message.chat.id,
        "🧵 Введите детали заказа (например: тип молнии, длина, количество):",
    )
    bot.register_next_step_handler(msg, handle_order)

def handle_order(message):
    order_text = message.text.strip()
    if not order_text:
        bot.send_message(message.chat.id, "Пожалуйста, введите детали заказа.")
        return

    # Ответ пользователю
    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Ваш заказ принят.\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=main_menu(),
    )

    # Уведомление админу
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
        print(f"[Ошибка отправки админу]: {e}")

# --- Flask Webhook ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "✅ YKK Shop Bot работает стабильно 24/7!", 200

# --- Запуск ---
if __name__ == "__main__":
    bot.remove_webhook()
    if WEBHOOK_URL:
        full_url = f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}"
        bot.set_webhook(url=full_url)
        print(f"🌐 Webhook установлен: {full_url}")
    else:
        print("⚠️ Переменная RENDER_EXTERNAL_URL не задана!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
