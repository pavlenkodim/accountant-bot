from datetime import datetime
from typing import List
from collections import defaultdict
import pytz
 
TIMEZONE = pytz.timezone("Asia/Almaty")
 
# Названия периодов
PERIOD_NAMES = {
    "week": "неделю",
    "month": "месяц",
    "quarter": "квартал",
}
 
MONTH_NAMES = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель",
    5: "май", 6: "июнь", 7: "июль", 8: "август",
    9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}
 
 
def format_amount(amount: float) -> str:
    """Форматирует сумму: 42700 → '42 700'"""
    return f"{amount:,.0f}".replace(",", " ")
 
 
def get_period_title(period: str) -> str:
    """Заголовок отчёта с датами."""
    now = datetime.now(TIMEZONE)
 
    if period == "week":
        from datetime import timedelta
        monday = now - timedelta(days=now.weekday())
        return f"📅 Неделя: {monday.strftime('%d.%m')} – {now.strftime('%d.%m.%Y')}"
 
    elif period == "month":
        return f"📅 {MONTH_NAMES[now.month].capitalize()} {now.year}"
 
    elif period == "quarter":
        q = (now.month - 1) // 3 + 1
        return f"📅 {q}-й квартал {now.year}"
 
    return f"📅 {now.strftime('%d.%m.%Y')}"
 
 
def generate_report(expenses: List[dict], period: str) -> str:
    """
    Генерирует текстовый отчёт по списку расходов.
 
    Возвращает HTML-строку для Telegram (parse_mode="HTML").
    """
    period_label = PERIOD_NAMES.get(period, period)
    title = get_period_title(period)
 
    # Нет расходов
    if not expenses:
        return (
            f"<b>📊 Отчёт за {period_label}</b>\n"
            f"{title}\n\n"
            "😌 Расходов не найдено.\n\n"
            "<i>Пишите расходы в чат в любом формате:\n"
            "• 1000 такси\n"
            "• 20 тыс куртка\n"
            "• 42 700 - продукты</i>"
        )
 
    # Группируем по категориям
    by_category = defaultdict(list)
    for exp in expenses:
        by_category[exp["category"]].append(exp)
 
    total = sum(exp["amount"] for exp in expenses)
 
    # Сортируем категории по убыванию суммы
    sorted_categories = sorted(
        by_category.items(),
        key=lambda x: sum(e["amount"] for e in x[1]),
        reverse=True,
    )
 
    lines = [
        f"<b>📊 Отчёт за {period_label}</b>",
        title,
        "",
    ]
 
    for category, cat_expenses in sorted_categories:
        cat_total = sum(e["amount"] for e in cat_expenses)
        percent = (cat_total / total * 100) if total > 0 else 0
 
        # Прогресс-бар (из блоков)
        bar_filled = round(percent / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
 
        lines.append(
            f"<b>{category}</b>  {format_amount(cat_total)} ₸  ({percent:.0f}%)"
        )
        lines.append(f"<code>{bar}</code>")
 
        # Детализация (топ-3 траты в категории)
        top_expenses = sorted(cat_expenses, key=lambda x: x["amount"], reverse=True)[:3]
        for exp in top_expenses:
            desc = exp["description"][:35]
            lines.append(f"  • {format_amount(exp['amount'])} ₸ — {desc}")
 
        if len(cat_expenses) > 3:
            lines.append(f"  <i>...и ещё {len(cat_expenses) - 3} трат</i>")
 
        lines.append("")
 
    # Итог
    lines += [
        "─" * 25,
        f"💰 <b>Итого: {format_amount(total)} ₸</b>",
        f"📝 Транзакций: {len(expenses)}",
        f"📊 Среднее: {format_amount(total / len(expenses))} ₸",
    ]
 
    # Добавляем топ-3 самых дорогих трат
    top3 = sorted(expenses, key=lambda x: x["amount"], reverse=True)[:3]
    if top3:
        lines += ["", "🏆 <b>Топ трат:</b>"]
        for i, exp in enumerate(top3, 1):
            lines.append(f"  {i}. {format_amount(exp['amount'])} ₸ — {exp['description'][:30]}")
 
    return "\n".join(lines)