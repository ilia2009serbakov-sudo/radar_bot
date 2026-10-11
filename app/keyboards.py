from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛰 Мой радар", callback_data="radar"),
         InlineKeyboardButton(text="🎯 Интересы", callback_data="topics")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
         InlineKeyboardButton(text="⭐ Premium", callback_data="premium")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="about")],
    ])


def topics_menu(topics: list[dict], limit: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"✓ {t['name']}", callback_data=f"topic_del:{t['slug']}")] for t in topics]
    if len(topics) < limit:
        rows.append([InlineKeyboardButton(text="➕ Добавить интерес", callback_data="topic_add")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topic_picker() -> InlineKeyboardMarkup:
    data = [
        ("💻 Технологии", "tech"), ("💰 Бизнес и деньги", "business"),
        ("🚗 Автомобили", "cars"), ("🎮 Игры", "games"),
        ("🔬 Наука", "science"), ("🎬 Кино и сериалы", "cinema"),
        ("⚽ Спорт", "sport"), ("🌐 Веб-разработка", "web"),
        ("🎨 Дизайн", "design"), ("📚 Образование", "education"),
    ]
    rows = []
    for i in range(0, len(data), 2):
        rows.append([InlineKeyboardButton(text=data[i][0], callback_data=f"topic_add:{data[i][1]}"),
                     InlineKeyboardButton(text=data[i + 1][0], callback_data=f"topic_add:{data[i + 1][1]}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_menu(enabled: bool, hour: int) -> InlineKeyboardMarkup:
    toggle = "🔕 Выключить дайджест" if enabled else "🔔 Включить дайджест"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="toggle_digest")],
        [InlineKeyboardButton(text=f"🕘 Время: {hour:02d}:00", callback_data="digest_hour")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="home")],
    ])


def hours_menu() -> InlineKeyboardMarkup:
    hours = [7, 8, 9, 10, 11, 12]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"hour:{h}") for h in hours[:3]],
        [InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"hour:{h}") for h in hours[3:]],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings")],
    ])


def premium_menu(invoice_url: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if invoice_url:
        rows.append([InlineKeyboardButton(text="⭐ Подключить Premium", url=invoice_url)])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def item_keyboard(item_key: str, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Полезно", callback_data=f"like:{item_key}"),
         InlineKeyboardButton(text="👎 Не моё", callback_data=f"dislike:{item_key}")],
        [InlineKeyboardButton(text="↗️ Открыть материал", url=url)],
    ])
