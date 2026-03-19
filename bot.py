"""
Telegram бот для учёта расходов в групповом чате.

Бот читает сообщения в группе, парсит расходы с помощью regex,
и формирует отчёты по запросу или автоматически (еженедельно/ежемесячно).

Установка зависимостей:
    pip install python-telegram-bot==20.7 apscheduler pytz

Запуск:
    python bot.py
"""

import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Загружаем переменные из файла .env
load_dotenv()

from parser import parse_expense
from reports import generate_report
from history import fetch_expenses_from_history, store_expense

# ─── Настройка логирования ────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Конфиг ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TIMEZONE = pytz.timezone("Asia/Almaty")  # Часовой пояс Казахстан

# ID чата группы (заполните после добавления бота в группу)
# Можно узнать командой /chatid в группе
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))


# ─── Обработчик текстовых сообщений ──────────────────────────────────────────
async def handle_message(update, context):
    """
    Слушает все сообщения в группе.
    Если сообщение похоже на расход — отвечает подтверждением.
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    expense = parse_expense(text)

    if expense:
        # Сохраняем расход в памяти бота
        user = update.message.from_user
        username = user.first_name or user.username or "Неизвестно"
        date = update.message.date.astimezone(TIMEZONE)
        store_expense(
            bot=context.bot,
            chat_id=update.effective_chat.id,
            expense=expense,
            date=date,
            user=username,
        )
        # Отправляем тихое подтверждение (без уведомления)
        await update.message.reply_text(
            f"✅ Записал: {expense['amount']:,} ₸ — {expense['category']} ({expense['description']})",
            disable_notification=True,
        )
        logger.info(f"Распознан расход от {username}: {expense}")


# ─── Команда /start ───────────────────────────────────────────────────────────
async def cmd_start(update, context):
    await update.message.reply_text(
        "👋 Привет! Я бот для учёта расходов.\n\n"
        "Просто пишите расходы в чат в любом формате:\n"
        "• <code>1000 такси</code>\n"
        "• <code>20 тыс куртка</code>\n"
        "• <code>42 700 - продукты</code>\n\n"
        "📊 <b>Команды для отчётов:</b>\n"
        "/week — отчёт за текущую неделю\n"
        "/month — отчёт за текущий месяц\n"
        "/quarter — отчёт за текущий квартал\n"
        "/chatid — узнать ID этого чата",
        parse_mode="HTML",
    )


# ─── Команда /chatid ──────────────────────────────────────────────────────────
async def cmd_chatid(update, context):
    """Показывает ID чата — нужно для настройки TARGET_CHAT_ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"ID этого чата: <code>{chat_id}</code>", parse_mode="HTML")


# ─── Команда /week ────────────────────────────────────────────────────────────
async def cmd_week(update, context):
    """Отчёт за текущую неделю (по истории чата)."""
    await update.message.reply_text("⏳ Собираю данные за неделю...")
    expenses = await fetch_expenses_from_history(context.bot, update.effective_chat.id, period="week")
    report = generate_report(expenses, period="week")
    await update.message.reply_text(report, parse_mode="HTML")


# ─── Команда /month ───────────────────────────────────────────────────────────
async def cmd_month(update, context):
    """Отчёт за текущий месяц (по истории чата)."""
    await update.message.reply_text("⏳ Собираю данные за месяц...")
    expenses = await fetch_expenses_from_history(context.bot, update.effective_chat.id, period="month")
    report = generate_report(expenses, period="month")
    await update.message.reply_text(report, parse_mode="HTML")


# ─── Команда /quarter ─────────────────────────────────────────────────────────
async def cmd_quarter(update, context):
    """Отчёт за текущий квартал (по истории чата)."""
    await update.message.reply_text("⏳ Собираю данные за квартал...")
    expenses = await fetch_expenses_from_history(context.bot, update.effective_chat.id, period="quarter")
    report = generate_report(expenses, period="quarter")
    await update.message.reply_text(report, parse_mode="HTML")


# ─── Автоматические отчёты ────────────────────────────────────────────────────
async def auto_weekly_report(bot):
    """Автоматический отчёт каждое воскресенье в 20:00."""
    if TARGET_CHAT_ID == 0:
        logger.warning("TARGET_CHAT_ID не задан, автоотчёт пропущен")
        return
    logger.info("Отправляю еженедельный отчёт...")
    expenses = await fetch_expenses_from_history(bot, TARGET_CHAT_ID, period="week")
    report = generate_report(expenses, period="week")
    await bot.send_message(chat_id=TARGET_CHAT_ID, text=report, parse_mode="HTML")


async def auto_monthly_report(bot):
    """Автоматический отчёт в последний день месяца в 21:00."""
    if TARGET_CHAT_ID == 0:
        logger.warning("TARGET_CHAT_ID не задан, автоотчёт пропущен")
        return
    logger.info("Отправляю ежемесячный отчёт...")
    expenses = await fetch_expenses_from_history(bot, TARGET_CHAT_ID, period="month")
    report = generate_report(expenses, period="month")
    await bot.send_message(chat_id=TARGET_CHAT_ID, text=report, parse_mode="HTML")


# ─── Главная функция ──────────────────────────────────────────────────────────
def main():
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("quarter", cmd_quarter))

    # Слушаем все текстовые сообщения в группах
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Планировщик автоматических отчётов
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Каждое воскресенье в 20:00
    scheduler.add_job(
        auto_weekly_report,
        CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=TIMEZONE),
        args=[app.bot],
        id="weekly_report",
    )

    # Последний день каждого месяца в 21:00
    scheduler.add_job(
        auto_monthly_report,
        CronTrigger(day="last", hour=21, minute=0, timezone=TIMEZONE),
        args=[app.bot],
        id="monthly_report",
    )

    scheduler.start()
    logger.info("Планировщик запущен")

    # Запускаем бота
    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()