from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, LabeledPrice, Message, PreCheckoutQuery

from app import db
from app.config import settings
from app.feeds import collect_items
from app.keyboards import hours_menu, item_keyboard, main_menu, premium_menu, settings_menu, topic_picker, topics_menu
from app.texts import ABOUT, PREMIUM, RETURNING, WELCOME
from app.topics import TOPICS, topic_name

bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
BANNER = Path(__file__).resolve().parent.parent / "assets" / "radar_banner.png"


@dp.message(CommandStart())
async def start(message: Message):
    user = await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    topics = await db.get_topics(message.from_user.id)
    if not topics:
        if BANNER.exists():
            await message.answer_photo(FSInputFile(BANNER), caption=WELCOME, reply_markup=topic_picker())
        else:
            await message.answer(WELCOME, reply_markup=topic_picker())
        return
    await message.answer(RETURNING.format(name=message.from_user.first_name or "друг"), reply_markup=main_menu())


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(ABOUT, reply_markup=main_menu())


@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(WELCOME, reply_markup=main_menu())


@dp.callback_query(F.data == "about")
async def about(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(ABOUT, reply_markup=main_menu())


@dp.callback_query(F.data == "premium")
async def premium(call: CallbackQuery):
    await call.answer()
    user = await db.get_user(call.from_user.id)
    now = datetime.now(timezone.utc)
    if user and user["premium_until"] and user["premium_until"] > now:
        await call.message.edit_text(
            f"⭐ <b>Premium активен</b>\n\nДо <b>{user['premium_until'].strftime('%d.%m.%Y')}</b>.\n\nСпасибо, что поддерживаешь Радар.",
            reply_markup=premium_menu(),
        )
        return
    invoice = await bot.create_invoice_link(
        title="Радар Premium",
        description="Расширенный персональный радар на 30 дней.",
        payload=f"radar_premium:{call.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Premium — 30 дней", amount=settings.premium_stars)],
        provider_token="",
        subscription_period=2592000,
    )
    await call.message.edit_text(PREMIUM, reply_markup=premium_menu(invoice))


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    until_ts = getattr(payment, "subscription_expiration_date", None)
    until = datetime.fromtimestamp(until_ts, tz=timezone.utc) if until_ts else datetime.now(timezone.utc)
    await db.set_premium(message.from_user.id, until)
    await message.answer(
        f"⭐ <b>Premium подключён</b>\n\nДоступ активен до <b>{until.strftime('%d.%m.%Y')}</b>.\n\nРадар продолжит работать автоматически.",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data == "topics")
async def topics(call: CallbackQuery):
    await call.answer()
    user_topics = await db.get_topics(call.from_user.id)
    user = await db.get_user(call.from_user.id)
    limit = settings.premium_topics_limit if user and user["plan"] == "premium" and user["premium_until"] and user["premium_until"] > datetime.now(timezone.utc) else settings.free_topics_limit
    body = "\n".join(f"• {t['name']}" for t in user_topics) or "Пока ничего нет."
    await call.message.edit_text(f"<b>🎯 Твои интересы</b>\n\n{body}\n\nВыбрано: <b>{len(user_topics)}/{limit}</b>", reply_markup=topics_menu(user_topics, limit))


@dp.callback_query(F.data == "topic_add")
async def topic_add_generic(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("<b>Выбери тему</b>\n\nМожно добавить несколько — Радар будет учитывать каждую.", reply_markup=topic_picker())


@dp.callback_query(F.data.startswith("topic_add:"))
async def topic_add(call: CallbackQuery):
    slug = call.data.split(":", 1)[1]
    if slug not in TOPICS:
        await call.answer("Неизвестная тема", show_alert=True)
        return
    user = await db.get_user(call.from_user.id)
    premium_active = bool(user and user["premium_until"] and user["premium_until"] > datetime.now(timezone.utc))
    limit = settings.premium_topics_limit if premium_active else settings.free_topics_limit
    if await db.count_topics(call.from_user.id) >= limit:
        await call.answer("Лимит достигнут. В Premium — до 20 интересов.", show_alert=True)
        return
    ok = await db.add_topic(call.from_user.id, topic_name(slug), slug)
    await call.answer("Добавлено 👍" if ok else "Этот интерес уже выбран.")
    user_topics = await db.get_topics(call.from_user.id)
    body = "\n".join(f"• {t['name']}" for t in user_topics)
    await call.message.edit_text(f"<b>🎯 Твои интересы</b>\n\n{body}\n\nМожно добавить ещё или открыть радар.", reply_markup=topics_menu(user_topics, limit))


@dp.callback_query(F.data.startswith("topic_del:"))
async def topic_del(call: CallbackQuery):
    await db.remove_topic(call.from_user.id, call.data.split(":", 1)[1])
    await call.answer("Удалено.")
    await topics(call)


@dp.callback_query(F.data == "settings")
async def settings_page(call: CallbackQuery):
    await call.answer()
    user = await db.get_user(call.from_user.id)
    await call.message.edit_text(
        "<b>⚙️ Настройки</b>\n\n"
        f"Ежедневный дайджест: <b>{'включён' if user['digest_enabled'] else 'выключен'}</b>\n"
        f"Время: <b>{user['digest_hour']:02d}:00</b> ({user['timezone']})\n\n"
        "Можно изменить время или полностью выключить автоматические подборки.",
        reply_markup=settings_menu(user["digest_enabled"], user["digest_hour"]),
    )


@dp.callback_query(F.data == "toggle_digest")
async def toggle_digest(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    new_value = not user["digest_enabled"]
    await db.set_digest(call.from_user.id, new_value)
    await call.answer("Настройки обновлены.")
    await settings_page(call)


@dp.callback_query(F.data == "digest_hour")
async def digest_hour(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("<b>🕘 Во сколько присылать дайджест?</b>", reply_markup=hours_menu())


@dp.callback_query(F.data.startswith("hour:"))
async def set_hour(call: CallbackQuery):
    hour = int(call.data.split(":", 1)[1])
    await db.set_digest_hour(call.from_user.id, hour)
    await call.answer(f"Дайджест — в {hour:02d}:00.")
    await settings_page(call)


@dp.callback_query(F.data == "radar")
async def radar(call: CallbackQuery):
    await call.answer()
    await send_radar(call.from_user.id, call.message)


@dp.callback_query(F.data.startswith("like:"))
async def like(call: CallbackQuery):
    await db.set_feedback(call.from_user.id, call.data.split(":", 1)[1], 1)
    await call.answer("Учту 👍")


@dp.callback_query(F.data.startswith("dislike:"))
async def dislike(call: CallbackQuery):
    await db.set_feedback(call.from_user.id, call.data.split(":", 1)[1], -1)
    await call.answer("Понял. Буду точнее 👌")


async def send_radar(user_id: int, message: Message | None = None):
    user = await db.get_user(user_id)
    premium_active = bool(user and user["premium_until"] and user["premium_until"] > datetime.now(timezone.utc))
    limit = settings.premium_items_per_digest if premium_active else settings.free_items_per_digest
    items = await db.get_unseen_for_user(user_id, limit)
    if not items:
        text = "🛰 <b>Радар пока пуст</b>\n\nСвежих материалов по твоим интересам пока нет. Я продолжу искать — загляни позже."
        if message:
            await message.edit_text(text, reply_markup=main_menu())
        else:
            await bot.send_message(user_id, text, reply_markup=main_menu())
        return

    intro = f"🛰 <b>Твой радар</b>\n\nНашёл <b>{len(items)}</b> свежих материалов. Оставил только то, что совпадает с твоими интересами."
    if message:
        await message.edit_text(intro, reply_markup=main_menu())
    else:
        await bot.send_message(user_id, intro)
    for item in items:
        text = f"<b>{item['title']}</b>\n\n{item['summary']}\n\n<i>{item['source']}</i>"
        await bot.send_message(user_id, text, reply_markup=item_keyboard(item["item_key"], item["url"]))
        await db.mark_delivered(user_id, item["id"])


async def refresh_and_deliver() -> int:
    collected = await collect_items()
    for item in collected:
        await db.save_item(item)

    now = datetime.now(timezone.utc)
    sent = 0
    for user in await db.get_users():
        try:
            tz = ZoneInfo(user["timezone"])
            local = now.astimezone(tz)
            if local.hour != user["digest_hour"]:
                continue
            await send_radar(user["telegram_id"])
            sent += 1
        except Exception:
            continue
    return sent
