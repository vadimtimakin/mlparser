-- Сообщения из канала/групп/топиков (для ингеста mlagent). Идемпотентно при старте.
-- Живёт в mlcrm-db рядом с inbox (личка). Колонки chat_id/chat_title/sender_id/
-- message_id/reply_to/text/sent_at читает существующий mlagent weekly-ингест.
CREATE TABLE IF NOT EXISTS chat_messages (
    id           BIGSERIAL PRIMARY KEY,
    chat_id      BIGINT NOT NULL,
    chat_title   TEXT,
    thread_id    BIGINT,                 -- message_thread_id (топик форума), NULL для обычных
    sender_id    BIGINT,
    message_id   BIGINT NOT NULL,
    reply_to     BIGINT,                 -- на какое сообщение ответ (для Q&A-цепочек)
    text         TEXT,
    has_voice    BOOLEAN NOT NULL DEFAULT FALSE,
    voice_ogg    BYTEA,                  -- байты голосового (ASR в mlagent), пара файлов
    sent_at      TIMESTAMPTZ NOT NULL,
    edited_at    TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sent ON chat_messages (sent_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat ON chat_messages (chat_id, thread_id);

-- Append-only сырой архив ВСЕХ сообщений (delete-proof бэкап): по строке на каждый
-- полученный апдейт, все типы, каждая правка — новая строка. Ничего не перезатирается/не
-- удаляется. Пишется ДО фильтра should_collect. Дублирует message_archive из
-- mlbot/crm_capture.py (личка пишет туда же) — держать DDL в синхроне.
CREATE TABLE IF NOT EXISTS message_archive (
    id                     BIGSERIAL PRIMARY KEY,
    source                 TEXT NOT NULL,          -- business | group | channel
    update_kind            TEXT NOT NULL,          -- new | edited | deleted
    business_connection_id TEXT,
    chat_id                BIGINT NOT NULL,
    chat_type              TEXT,
    chat_title             TEXT,
    thread_id              BIGINT,
    direction              TEXT,
    sender_id              BIGINT,
    sender_username        TEXT,
    sender_name            TEXT,
    message_id             BIGINT,
    reply_to               BIGINT,
    text                   TEXT,
    media_type             TEXT,
    file_id                TEXT,
    file_unique_id         TEXT,
    file_name              TEXT,
    sent_at                TIMESTAMPTZ,
    edited_at              TIMESTAMPTZ,
    raw_json               JSONB,
    archived_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_archive_chat_msg ON message_archive (chat_id, message_id);
CREATE INDEX IF NOT EXISTS idx_archive_archived ON message_archive (archived_at);
