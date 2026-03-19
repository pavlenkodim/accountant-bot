"""
Парсер расходов на основе регулярных выражений.

Поддерживает форматы:
    1000 такси
    20 тыс куртка
    42 700 - продукты
    потратил 5000 на еду
    кофе 350
    1.5к бензин
    куртка 20000
"""

import re
from typing import Optional

# ─── Категории и ключевые слова ───────────────────────────────────────────────
CATEGORIES = {
    "🚕 Транспорт": [
        "такси", "uber", "убер", "yandex", "яндекс", "автобус", "метро",
        "бензин", "топливо", "парковка", "проезд", "транспорт", "bolt",
        "маршрутка", "трамвай", "поезд", "билет", "авиа", "самолёт",
    ],
    "🛒 Продукты": [
        "продукты", "еда", "магазин", "супермаркет", "grocery", "овощи",
        "фрукты", "мясо", "молоко", "хлеб", "рынок", "базар", "astyk",
        "small", "смол", "magnum", "малина", "дастархан",
    ],
    "🍽️ Кафе и рестораны": [
        "кафе", "ресторан", "cafe", "restaurant", "обед", "ужин", "завтрак",
        "кофе", "coffee", "чай", "пицца", "суши", "фастфуд", "kfc", "mcdonalds",
        "макдак", "бургер", "доставка", "wolt", "glovo",
    ],
    "👗 Одежда": [
        "одежда", "куртка", "штаны", "джинсы", "рубашка", "обувь", "кроссовки",
        "ботинки", "пальто", "свитер", "платье", "футболка", "носки",
    ],
    "💊 Здоровье": [
        "аптека", "лекарство", "таблетки", "врач", "доктор", "больница",
        "клиника", "анализы", "витамины", "pharmacy", "медицина",
    ],
    "🏠 Дом и ЖКУ": [
        "квартплата", "аренда", "коммуналка", "свет", "газ", "вода",
        "интернет", "телефон", "связь", "ремонт", "мебель", "ikea",
    ],
    "🎮 Развлечения": [
        "кино", "cinema", "игры", "game", "подписка", "netflix", "spotify",
        "развлечения", "театр", "концерт", "спорт", "фитнес", "зал",
    ],
    "📚 Образование": [
        "курсы", "книги", "обучение", "учёба", "школа", "университет",
        "репетитор", "урок", "education",
    ],
    "✂️ Красота": [
        "парикмахер", "стрижка", "маникюр", "педикюр", "косметика",
        "салон", "beauty", "крем", "шампунь",
    ],
    "🐾 Животные": [
        "ветеринар", "корм", "питомец", "кошка", "собака", "зоомагазин",
    ],
    "💸 Прочее": [],
}


def extract_amount(text: str) -> Optional[tuple[float, str]]:
    """
    Ищет сумму в тексте и возвращает (число, найденная_строка) или None.

    Стратегия: сначала ищем формат "42 700" (число с пробелом-разделителем тысяч),
    потом обычные числа с суффиксами тыс/к/млн.
    """

    # 1. Формат с пробелом как разделителем тысяч: "42 700", "1 000 000"
    #    Паттерн: 1-3 цифры, затем РОВНО группы по 3 цифры через пробел
    spaced = re.search(
        r"\b(\d{1,3}(?:\s\d{3})+)\b",
        text
    )
    if spaced:
        raw = spaced.group(1)
        # Убираем пробелы и конвертируем
        amount = float(raw.replace(" ", ""))
        return amount, raw

    # 2. Обычное число (без пробелов) с необязательным суффиксом
    #    Примеры: 1000, 1000тыс, 20тыс, 1.5к, 500к
    plain = re.search(
        r"\b(\d+(?:[.,]\d+)?)(\s*(?:тыс(?:яч)?|тысяч|млн|million)|\s*[kкK](?=[^а-яёa-zA-Z]|$))?\b",
        text,
        re.IGNORECASE,
    )
    if plain:
        raw_num = plain.group(1).replace(",", ".")
        suffix = (plain.group(2) or "").strip().lower()
        try:
            amount = float(raw_num)
        except ValueError:
            return None

        if re.match(r"тыс|тысяч", suffix):
            amount *= 1000
        elif re.match(r"млн|million", suffix):
            amount *= 1_000_000
        elif re.match(r"[kкK]", suffix):
            amount *= 1000

        full_match = plain.group(0).strip()
        return amount, full_match

    return None


def detect_category(text: str) -> tuple[str, str]:
    """
    Определяет категорию и описание по тексту.
    Возвращает (категория, описание).
    """
    text_lower = text.lower()

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                return category, kw.capitalize()

    # Категория не определена — берём первое значимое слово
    words = re.findall(r"[а-яёa-z]+", text_lower)
    stop_words = {
        "на", "за", "и", "в", "с", "по", "из", "от", "до",
        "потратил", "потратила", "купил", "купила", "заплатил", "заплатила",
    }
    description = next(
        (w.capitalize() for w in words if w not in stop_words), "Расход"
    )
    return "💸 Прочее", description


def parse_expense(text: str) -> Optional[dict]:
    """
    Главная функция: парсит строку и возвращает словарь расхода или None.

    Форматы (порядок числа и описания — любой):
        1000 такси
        куртка 20000
        42 700 - продукты
        потратил 5000 на еду
        20 тыс куртка
        1.5к бензин

    Возвращает:
        {
            "amount": float,
            "category": str,
            "description": str,
            "raw": str,
        }
        или None если расход не распознан.
    """
    text = text.strip()

    # Игнорируем короткие сообщения и команды
    if len(text) < 2 or text.startswith("/"):
        return None

    result = extract_amount(text)
    if result is None:
        return None

    amount, raw_match = result

    # Минимальный порог — 10 тенге
    if amount < 10:
        return None

    # Убираем найденную сумму из текста → остаток = описание
    description_text = text.replace(raw_match, "", 1).strip(" -—,:.")

    # Определяем категорию по полному тексту
    category, fallback_description = detect_category(text)

    # Финальное описание
    final_description = description_text[:40] if description_text else fallback_description

    return {
        "amount": amount,
        "category": category,
        "description": final_description or fallback_description,
        "raw": text,
    }