"""mlparser — тонкий бот-коллектор (aiogram 3.x).

Слушает канал + заданные топики общего чата + весь чат работы и пишет сообщения в
mlcrm-db (chat_messages). ML здесь нет — дистилляцию/эмбеддинги делает mlagent.

Запуск: python bot.py  (нужны COLLECTOR_BOT_TOKEN и MLCRM_DATABASE_URL).
Discovery: DISCOVER=1 → логирует chat_id/thread_id всех входящих; /whereami в чате/
топике печатает его id (для заполнения env-переменных источников).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

import config as cfg
import db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("mlparser")
router = Router()


async def _store(m: Message, bot: Bot, *, edited: bool) -> None:
    chat_id = m.chat.id
    thread_id = m.message_thread_id
    if cfg.DISCOVER:
        log.info("seen chat_id=%s thread_id=%s type=%s title=%r",
                 chat_id, thread_id, m.chat.type, m.chat.title)
    if not cfg.should_collect(chat_id, thread_id):
        return

    text = m.text or m.caption
    voice = m.voice or m.audio
    has_voice = voice is not None
    voice_ogg = None
    if has_voice and (not voice.file_size or voice.file_size <= cfg.MAX_VOICE_BYTES):
        try:
            buf = await bot.download(voice)
            voice_ogg = buf.read()
        except Exception as e:  # noqa: BLE001
            log.warning("не скачал голосовое: %s", e)
    if not text and not has_voice:
        return  # фото/стикер/служебное без текста — пропускаем

    reply_to = None
    r = m.reply_to_message
    if r is not None and not getattr(r, "forum_topic_created", None):
        reply_to = r.message_id

    edited_at = None
    if edited and m.edit_date:
        edited_at = datetime.fromtimestamp(m.edit_date, tz=timezone.utc)

    try:
        await asyncio.to_thread(
            db.upsert_message,
            chat_id=chat_id, chat_title=m.chat.title, thread_id=thread_id,
            sender_id=(m.from_user.id if m.from_user else None),
            message_id=m.message_id, reply_to=reply_to, text=text,
            has_voice=has_voice, voice_ogg=voice_ogg, sent_at=m.date,
            edited_at=edited_at,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("ошибка записи в БД: %s", e)


@router.message(Command("whereami"))
async def whereami(m: Message) -> None:
    if m.from_user and cfg.ADMIN_IDS and m.from_user.id not in cfg.ADMIN_IDS:
        return
    await m.reply(
        f"chat_id: <code>{m.chat.id}</code>\n"
        f"thread_id (топик): <code>{m.message_thread_id}</code>\n"
        f"type: {m.chat.type}\ntitle: {m.chat.title}",
        parse_mode="HTML",
    )


@router.channel_post()
async def on_channel_post(m: Message, bot: Bot) -> None:
    await _store(m, bot, edited=False)


@router.edited_channel_post()
async def on_edited_channel_post(m: Message, bot: Bot) -> None:
    await _store(m, bot, edited=True)


@router.edited_message()
async def on_edited_message(m: Message, bot: Bot) -> None:
    await _store(m, bot, edited=True)


@router.message()
async def on_message(m: Message, bot: Bot) -> None:
    await _store(m, bot, edited=False)


async def main() -> None:
    if not cfg.TOKEN:
        raise SystemExit("COLLECTOR_BOT_TOKEN не задан")
    if not db.enabled():
        raise SystemExit("MLCRM_DATABASE_URL / DATABASE_URL не задан")
    await asyncio.to_thread(db.init_schema)
    bot = Bot(cfg.TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    log.info("mlparser запущен. DISCOVER=%s | channel=%s general=%s(topics=%s) work=%s",
             cfg.DISCOVER, cfg.CHANNEL_ID, cfg.GROUP_GENERAL_ID,
             sorted(cfg.GENERAL_TOPIC_IDS), cfg.GROUP_WORK_ID)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
