import os
import sys
import signal
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Message
)

from bot.notifier import notify_admin
from bot.responder import get_openai_client, generate_response


# ----------------------------
# Конфиг и логирование
# ----------------------------
def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Ротация локального файла (10 МБ × 5)
    rotating = RotatingFileHandler("logs/bot.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    rotating.setFormatter(fmt)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=[rotating, stream])


def load_config():
    # В контейнере env приходит через compose; load_dotenv() не мешает при локальном запуске.
    load_dotenv()
    token = os.getenv("TOKEN_TG")
    openai_key = os.getenv("OPENAI_KEY")
    admin_id = os.getenv("ADMIN_ID")  # может понадобиться notify_admin
    if not token or not openai_key:
        logging.critical("❌ Переменные окружения TOKEN_TG/OPENAI_KEY не заданы")
        sys.exit(1)
    return token, openai_key, admin_id


# ----------------------------
# Инициализация
# ----------------------------
setup_logging()
TOKEN_TG, OPENAI_KEY, ADMIN_ID = load_config()

bot = telebot.TeleBot(
    TOKEN_TG,
    parse_mode=None,                 # можно "HTML" или "MarkdownV2", если потребуется
    disable_web_page_preview=True
)
logger = logging.getLogger("scandi-bot")
client = get_openai_client(OPENAI_KEY)


# ----------------------------
# UI: клавиатуры
# ----------------------------
def main_reply_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🌍 Открыть меню миров"))
    return kb


def worlds_inline_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        # InlineKeyboardButton("🛡️ В Скандинавию", url="https://t.me/name_scandi_bot"),
        InlineKeyboardButton("🌾 В Славянщину", url="https://t.me/name_slavic_bot"),
        InlineKeyboardButton("🍀 В Кельтию", url="https://t.me/name_kelt_bot"),
    )
    return kb


# ----------------------------
# Хендлеры
# ----------------------------
@bot.message_handler(commands=["start", "help"])
def cmd_start(message: Message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Напиши любое имя — я шуточно «докажу», что оно скандинавское.\n\n"
        "• Нажми «🌍 Открыть меню миров», чтобы перейти в другие боты.\n"
        "• /help — эта подсказка.",
        reply_markup=main_reply_kb(),
    )


@bot.message_handler(func=lambda m: isinstance(m.text, str) and m.text.strip() == "🌍 Открыть меню миров")
def open_worlds_menu(message: Message):
    bot.send_message(
        message.chat.id,
        "⚔️ Два пути открыты перед тобой, путник:\nВыбери, в каком мире хочешь узнать тайны имён.",
        reply_markup=worlds_inline_kb(),
    )


@bot.message_handler(content_types=["text"])
def handle_text(message: Message):
    text = (message.text or "").strip()
    if not text or text == "🌍 Открыть меню миров":
        return

    username = message.from_user.username or "без_ника"
    prompt = f"Шуточно докажи, что имя {text} — скандинавское."

    logger.info("Запрос от @%s: %s", username, text)
    try:
        reply = generate_response(client, prompt)
        # Телеграм ограничивает длину; на всякий случай обрежем до ~4000 символов
        reply = (reply or "").strip()
        if len(reply) > 3900:
            reply = reply[:3900] + "…"
        bot.send_message(message.chat.id, reply)
    except Exception as e:
        logger.exception("Ошибка при генерации ответа")
        bot.send_message(message.chat.id, "⚠️ Упс! Что-то пошло не так.")
        # уведомление админу — не валим поток, если notify_admin падает
        try:
            notify_admin(f"❌ Ошибка у @{username}: {e}")
        except Exception:
            logger.warning("Не удалось отправить notify_admin", exc_info=True)


@bot.message_handler(func=lambda _: True, content_types=["photo", "sticker", "audio", "video", "document", "voice", "contact", "location", "poll"])
def ignore_non_text(message: Message):
    bot.send_message(message.chat.id, "Я понимаю только текст: напиши имя, и я попробую доказать, что оно из Скандинавии 😉")


# ----------------------------
# Запуск и корректное завершение
# ----------------------------
_shutdown = False


def _graceful_exit(signum, _frame):
    global _shutdown
    if not _shutdown:
        _shutdown = True
        logger.info("Получен сигнал %s, останавливаемся…", signum)
        try:
            bot.stop_polling()
        except Exception:
            pass
        # даём немного времени на завершение потоков
        sys.exit(0)


signal.signal(signal.SIGINT, _graceful_exit)
signal.signal(signal.SIGTERM, _graceful_exit)


def main():
    try:
        logger.info("🤖 Бот запущен")
        try:
            notify_admin("✅ Бот стартовал и готов к бою.")
        except Exception:
            logger.warning("Не удалось отправить notify_admin о старте", exc_info=True)

        # threaded=False — предсказуемее завершение; long polling с автоповтором
        bot.infinity_polling(
            timeout=30,                 # таймаут long-poll запроса
            long_polling_timeout=30,    # серверный таймаут
            request_timeout=60,         # сетевой таймаут
            interval=0,                 # без задержки между циклами
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        logger.critical("Бот упал критически", exc_info=True)
        try:
            notify_admin(f"🚨 Критическая ошибка бота:\n{e}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
