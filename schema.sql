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
