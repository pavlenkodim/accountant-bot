from datetime import datetime, timedelta
from typing import List
import pytz
 
from parser import parse_expense
 
TIMEZONE = pytz.timezone("Asia/Almaty")
 
 
def get_period_range(period: str) -> tuple[datetime, datetime]:
    """
    Возвращает начало и конец периода (с учётом часового пояса).
 
    Периоды: "week", "month", "quarter"
    """
    now = datetime.now(TIMEZONE)
 
    if period == "week":
        # Начало недели = понедельник текущей недели
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
 
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
 
    elif period == "quarter":
        # Квартал: Q1=янв-мар, Q2=апр-июн, Q3=июл-сен, Q4=окт-дек
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
 
    else:
        # По умолчанию — текущий день
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
 
    return start, end
 
 
async def fetch_expenses_from_history(bot, chat_id: int, period: str) -> List[dict]:
    """
    Получает расходы из накопленного хранилища бота за указанный период.
 
    bot.bot_data["expenses"] — список всех расходов с момента запуска бота.
    Каждый элемент: {"amount", "category", "description", "raw", "date", "user"}
    """
    # Получаем данные из памяти бота
    expenses_storage = getattr(bot, "_expenses_storage", {})
    all_expenses = expenses_storage.get(chat_id, [])
 
    start, end = get_period_range(period)
 
    # Фильтруем по периоду
    filtered = [
        exp for exp in all_expenses
        if start <= exp["date"] <= end
    ]
 
    return filtered
 
 
def store_expense(bot, chat_id: int, expense: dict, date: datetime, user: str):
    """
    Сохраняет распознанный расход в памяти бота.
 
    Вызывается из handle_message в bot.py при каждом успешном парсинге.
    """
    if not hasattr(bot, "_expenses_storage"):
        bot._expenses_storage = {}
 
    if chat_id not in bot._expenses_storage:
        bot._expenses_storage[chat_id] = []
 
    bot._expenses_storage[chat_id].append({
        **expense,
        "date": date,
        "user": user,
    })