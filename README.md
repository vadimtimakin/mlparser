# mlparser

Тонкий бот-коллектор для RAG-ассистента (**mlagent**). Слушает Telegram и пишет
новые сообщества-сообщения в Postgres (**mlcrm-db**, таблица `chat_messages`),
откуда их читает недельный ингест mlagent (дистилляция + эмбеддинги + Qdrant).

**ML здесь нет** — только сбор. Вся тяжёлая обработка остаётся в mlagent.

## Что собирает

- **Основной канал** → `channel` (материалы)
- **Общий чат**, только топики «Важное» и «Полезные материалы» → `important_general` / `useful_materials`
- **Чат работы** целиком: переписки → `chat_work`, топик «Важное» → `important_work`

Роутинг топик→слой делает mlagent по `chat_id` + `thread_id`; mlparser лишь
складывает сообщения с этими полями. Голосовые качает в БД (`voice_ogg`) — ASR в mlagent.
Бэкфилл июнь→сейчас идёт отдельно (ручной экспорт → парсер mlagent), бот ловит только новое.

## Архитектура

```
Telegram → mlparser (этот бот) → mlcrm-db.chat_messages → mlagent (ingest) → Qdrant
```

## Переменные окружения (Railway)

| Переменная | Назначение |
|---|---|
| `COLLECTOR_BOT_TOKEN` | токен бота-коллектора (у @BotFather `/setprivacy` → **Disable**) |
| `MLCRM_DATABASE_URL` | Postgres mlcrm-db (`${{mlcrm-db.DATABASE_URL}}`) |
| `CHANNEL_ID` | id основного канала |
| `GROUP_GENERAL_ID` | id общего чата (супергруппа-форум) |
| `GENERAL_TOPIC_IDS` | thread_id топиков «Важное»,«Полезные» через запятую |
| `GROUP_WORK_ID` | id чата работы |
| `ADMIN_IDS` | кто может звать `/whereami` (через запятую; дефолт — ментор) |
| `DISCOVER` | `1` — логировать id всех входящих (для поиска id источников) |
| `MAX_VOICE_BYTES` | лимит скачивания голосовых, дефолт 20МБ |

## Как узнать id источников (discovery)

1. Создать бота у @BotFather, `/setprivacy` → **Disable**. Добавить его: в канал —
   админом, в обе группы — участником.
2. Задеплоить с `DISCOVER=1` (id источников можно пока не ставить).
3. В каждом нужном **топике** и в чатах отправить `/whereami` — бот ответит
   `chat_id` и `thread_id`. Для канала — посмотреть `chat_id` в логах (бот логирует
   входящие посты). Либо просто смотреть строки `seen chat_id=… thread_id=…` в логах.
4. Проставить `CHANNEL_ID` / `GROUP_GENERAL_ID` / `GENERAL_TOPIC_IDS` / `GROUP_WORK_ID`,
   убрать `DISCOVER`, передеплоить — пойдёт реальный сбор.

## Деплой

Отдельный сервис на Railway (worker, без web-порта): `python bot.py`. Токен бота
потребляется только этим процессом — не вешать тот же токен на другой поллер (409).
