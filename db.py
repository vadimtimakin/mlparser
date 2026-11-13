"""Доступ к Postgres mlcrm-db (psycopg3, синхронно). Схема идемпотентна при старте.
Из async-хендлеров вызывать через asyncio.to_thread, чтобы не блокировать event loop."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from config import DATABASE_URL

ROOT = Path(__file__).resolve().parent


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u


def _conn():
    return psycopg.connect(_normalize_url(DATABASE_URL), autocommit=True)


def enabled() -> bool:
    return bool(DATABASE_URL)


def init_schema() -> None:
    sql = (ROOT / "schema.sql").read_text(encoding="utf-8")
    with _conn() as conn:
        for stmt in (s.strip() for s in sql.split(";")):
            if stmt:
                conn.execute(stmt)


def upsert_message(*, chat_id: int, chat_title: str | None, thread_id: int | None,
                   sender_id: int | None, message_id: int, reply_to: int | None,
                   text: str | None, has_voice: bool, voice_ogg: bytes | None,
                   sent_at: datetime, edited_at: datetime | None) -> None:
    """Вставка/обновление по (chat_id, message_id) — идемпотентно (правки, перекрытие бэкфилла)."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages
                (chat_id, chat_title, thread_id, sender_id, message_id, reply_to,
                 text, has_voice, voice_ogg, sent_at, edited_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (chat_id, message_id) DO UPDATE SET
                text = EXCLUDED.text,
                chat_title = EXCLUDED.chat_title,
                thread_id = COALESCE(EXCLUDED.thread_id, chat_messages.thread_id),
                has_voice = EXCLUDED.has_voice,
                voice_ogg = COALESCE(EXCLUDED.voice_ogg, chat_messages.voice_ogg),
                edited_at = EXCLUDED.edited_at
            """,
            (chat_id, chat_title, thread_id, sender_id, message_id, reply_to,
             text, has_voice, voice_ogg, sent_at, edited_at),
        )


def archive_message(*, source: str, update_kind: str, chat_id: int, chat_type: str | None,
                    chat_title: str | None, thread_id: int | None, sender_id: int | None,
                    sender_username: str | None, sender_name: str | None, message_id: int,
                    reply_to: int | None, text: str | None, media_type: str | None,
                    file_id: str | None, file_unique_id: str | None, file_name: str | None,
                    sent_at: datetime, edited_at: datetime | None, raw_json: dict | None) -> None:
    """Append-only запись в message_archive. Без upsert: каждая правка — отдельная строка."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO message_archive (source, update_kind, chat_id, chat_type, chat_title,
                thread_id, sender_id, sender_username, sender_name, message_id, reply_to,
                text, media_type, file_id, file_unique_id, file_name, sent_at, edited_at, raw_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (source, update_kind, chat_id, chat_type, chat_title, thread_id, sender_id,
             sender_username, sender_name, message_id, reply_to, text, media_type, file_id,
             file_unique_id, file_name, sent_at, edited_at,
             Jsonb(raw_json) if raw_json is not None else None),
        )
