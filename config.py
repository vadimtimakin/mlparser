"""Конфиг mlparser — тонкого бота-коллектора.

Собирает сообщения из канала + заданных топиков общего чата + всего чата работы
и пишет их в Postgres mlcrm-db (таблица chat_messages), откуда их читает ингест
mlagent. ML здесь нет — только сбор.

Все id — через env (заполняются после discovery). Пока id нет — ничего не
собираем (discovery-режим: /whereami + лог входящих).
"""
import os


def _int(name: str):
    v = os.getenv(name, "").strip()
    return int(v) if v else None


def _ints(name: str) -> set[int]:
    raw = os.getenv(name, "").replace(" ", "")
    return {int(x) for x in raw.split(",") if x}


TOKEN = os.getenv("COLLECTOR_BOT_TOKEN", "").strip()
# пишем в ту же БД, что читает mlagent (mlcrm-db)
DATABASE_URL = (os.getenv("MLCRM_DATABASE_URL", "").strip()
                or os.getenv("DATABASE_URL", "").strip())

MENTOR_ID = int(os.getenv("MENTOR_ID", "8138945053"))
ADMIN_IDS = _ints("ADMIN_IDS") or {MENTOR_ID}

# --- источники (id проставим после discovery) ---
CHANNEL_ID = _int("CHANNEL_ID")            # основной канал
GROUP_GENERAL_ID = _int("GROUP_GENERAL_ID")  # общий чат (супергруппа-форум)
GROUP_WORK_ID = _int("GROUP_WORK_ID")      # чат работы (супергруппа)
# топики общего чата, которые собираем: «Важное» + «Полезные материалы»
GENERAL_TOPIC_IDS = _ints("GENERAL_TOPIC_IDS")

DISCOVER = os.getenv("DISCOVER", "").strip() not in ("", "0", "false", "False")
MAX_VOICE_BYTES = int(os.getenv("MAX_VOICE_BYTES", str(20 * 1024 * 1024)))  # качаем голос до 20МБ


def should_collect(chat_id: int, thread_id: int | None) -> bool:
    """Собираем ли это сообщение (по вайтлисту источников)."""
    if CHANNEL_ID is not None and chat_id == CHANNEL_ID:
        return True
    if GROUP_WORK_ID is not None and chat_id == GROUP_WORK_ID:
        return True  # весь чат работы (переписки + топик «Важное» внутри по thread_id)
    if GROUP_GENERAL_ID is not None and chat_id == GROUP_GENERAL_ID:
        # из общего чата — ТОЛЬКО заданные топики (не вся болтовня)
        return bool(GENERAL_TOPIC_IDS) and thread_id in GENERAL_TOPIC_IDS
    return False
