TOPICS = {
    "tech": ("Технологии", ["технолог", "ai", "искусствен", "python", "программ", "разработ", "software", "open source", "нейросет"]),
    "business": ("Бизнес и деньги", ["бизнес", "стартап", "предприним", "рынок", "деньги", "инвест", "продаж", "финанс"]),
    "cars": ("Автомобили", ["автомоб", "машин", "bmw", "mercedes", "porsche", "toyota", "tesla", "авто", "motor"]),
    "games": ("Игры", ["игр", "steam", "playstation", "xbox", "nintendo", "game", "gaming"]),
    "science": ("Наука", ["наук", "исследован", "космос", "физик", "биолог", "астроном", "space"]),
    "cinema": ("Кино и сериалы", ["фильм", "сериал", "кино", "netflix", "актер", "режиссер", "movie"]),
    "sport": ("Спорт", ["спорт", "футбол", "баскетбол", "теннис", "хоккей", "формул", "football"]),
    "web": ("Веб-разработка", ["html", "css", "javascript", "frontend", "backend", "сайт", "веб-разработ", "react"]),
    "design": ("Дизайн", ["дизайн", "figma", "ux", "ui", "график", "типограф"]),
    "education": ("Образование", ["образован", "учеб", "курс", "экзамен", "школ", "университет", "обучен"]),
}


def topic_name(slug: str) -> str:
    return TOPICS.get(slug, (slug, []))[0]


def classify(text: str) -> list[str]:
    lowered = text.lower()
    scored: list[tuple[int, str]] = []
    for slug, (_, keywords) in TOPICS.items():
        score = sum(1 for word in keywords if word in lowered)
        if score:
            scored.append((score, slug))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [slug for _, slug in scored[:3]]
