import os
import re
import logging
import time
import telebot
from dotenv import load_dotenv
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.notifier import notify_admin
from bot.responder import get_openai_client, generate_response

# Логирование
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Переменные окружения
load_dotenv()
TOKEN_TG = os.getenv("TOKEN_TG")
OPENAI_KEY = os.getenv("OPENAI_KEY")

if not TOKEN_TG or not OPENAI_KEY:
    logging.error("❌ Переменные окружения не заданы")
    exit(1)

bot = telebot.TeleBot(TOKEN_TG)
client = get_openai_client(OPENAI_KEY)

NETWORK_ERROR_MARKERS = (
    "remotedisconnected",
    "network is unreachable",
    "read timed out",
    "connection aborted",
    "failed to establish a new connection",
    "max retries exceeded",
)
ADMIN_ALERT_COOLDOWN_SECONDS = 15 * 60
_last_admin_alert_at = 0.0


def sanitize_error_text(text: str) -> str:
    """Removes sensitive credentials from exception text."""
    sanitized = text
    if TOKEN_TG:
        sanitized = sanitized.replace(TOKEN_TG, "***")
    sanitized = re.sub(r"/bot\d+:[^/\s?]+", "/bot***", sanitized)
    return sanitized


def is_transient_network_error(error: Exception) -> bool:
    error_text = sanitize_error_text(str(error)).lower()
    return any(marker in error_text for marker in NETWORK_ERROR_MARKERS)


def notify_admin_throttled(prefix: str, error: Exception):
    global _last_admin_alert_at

    now = time.time()
    if now - _last_admin_alert_at < ADMIN_ALERT_COOLDOWN_SECONDS:
        logging.warning("Уведомление админу пропущено из-за cooldown")
        return

    notify_admin(f"{prefix}\n{sanitize_error_text(str(error))}")
    _last_admin_alert_at = now


@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🌍 Открыть меню миров"))

    bot.send_message(
        message.chat.id,
        "👋 Привет! Напиши любое имя — я попробую шуточно доказать, что оно скандинавское!\n\n"
        "🌟 Или выбери, куда хочешь отправиться:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: message.text == "🌍 Открыть меню миров")
def menu_button_handler(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        # InlineKeyboardButton("🛡️ В Скандинавию", url="https://t.me/name_scandi_bot"),
        InlineKeyboardButton("🌾 В Славянщину", url="https://t.me/name_slavic_bot"),
        InlineKeyboardButton("🍀 В Кельтию", url="https://t.me/name_kelt_bot")
    )

    bot.send_message(
        message.chat.id,
        "⚔️ Два пути открыты перед тобой, путник:\n"
        "Выбери, в каком мире хочешь узнать тайны имён.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "🌍 Открыть меню миров":
        return 
    user_input = message.text.strip()
    username = message.from_user.username or "без ника"
    prompt = f"Шуточно докажи, что имя {user_input} — скандинавское."
    logging.info(f"Запрос от @{username}: {user_input}")

    try:
        response = generate_response(client, prompt)
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logging.exception("Ошибка при генерации ответа")
        bot.send_message(message.chat.id, "⚠️ Упс! Что-то пошло не так.")
        notify_admin(f"❌ Ошибка у @{username}:\n{sanitize_error_text(str(e))}")


if __name__ == "__main__":
    failures = 0
    logging.info("🤖 Бот запущен")

    while True:
        poll_started_at = time.time()

        try:
            bot.polling(none_stop=True, interval=0, timeout=20, long_polling_timeout=20)
            logging.warning("Polling остановился без исключения, запускаю заново")
            if time.time() - poll_started_at > 120:
                failures = 0
            failures += 1
        except Exception as e:
            if time.time() - poll_started_at > 120:
                failures = 0
            failures += 1
            safe_error = sanitize_error_text(str(e))

            if is_transient_network_error(e):
                logging.warning("Сетевой сбой polling: %s", safe_error)
            else:
                logging.critical("Бот упал критически", exc_info=e)
                notify_admin_throttled("🚨 Критическая ошибка бота:", e)

        retry_delay = min(2 ** min(failures, 6), 60)
        logging.info("Перезапуск polling через %s сек", retry_delay)
        time.sleep(retry_delay)
