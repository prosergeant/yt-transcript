# YouTube Transcript Microservice

Микросервис для извлечения субтитров из YouTube видео.

## Эндпоинты

```
GET /transcript/{video_id}?lang=ru&format=full
GET /transcript?url=https://youtu.be/...&lang=ru&format=text
```

### Параметры

| Параметр | Тип    | По умолчанию | Описание                          |
|----------|--------|--------------|-----------------------------------|
| `lang`   | string | `ru`         | Код языка субтитров               |
| `format` | string | `full`       | `full` — с чанками, `text` — только текст |

### Примеры

```bash
# По video ID
curl https://your-service.onrender.com/transcript/J53r2F7w6QQ

# По URL
curl "https://your-service.onrender.com/transcript?url=https://youtu.be/J53r2F7w6QQ&lang=ru&format=text"
```

### Ответ `format=full`

```json
{
  "video_id": "J53r2F7w6QQ",
  "text": "полный текст субтитров...",
  "duration_seconds": 1234,
  "chunks_count": 312,
  "chunks": [
    { "text": "привет", "start": 0.5, "duration": 1.2 },
    ...
  ]
}
```

### Ответ `format=text`

```json
{
  "video_id": "J53r2F7w6QQ",
  "text": "полный текст субтитров одной строкой..."
}
```

## Деплой на Render.com

1. Форкни/пуши репозиторий на GitHub
2. Зайди на [render.com](https://render.com) → New → Web Service
3. Подключи репозиторий
4. Runtime: **Docker**
5. Бесплатный план (Free)
6. Deploy

## Локальный запуск

```bash
# Через Docker
docker build -t yt-transcript .
docker run -p 8000:8000 yt-transcript

# Напрямую
pip install -r requirements.txt
uvicorn main:app --reload
```

Документация доступна по адресу `http://localhost:8000/docs`