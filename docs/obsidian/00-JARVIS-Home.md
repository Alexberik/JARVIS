# JARVIS — Home

Локальный ассистент на твоём ПК.

## Как это устроено

```
Ты (текст / голос)
  → JARVIS Web UI http://127.0.0.1:8765
  → Agent Router
      ├── Rules + Tools (погода, задачи, заметки)
      ├── LLM (Ollama) — следующий этап
      └── Voice STT/TTS — scaffold
  → Obsidian (Local REST API)
```

## Папка JARVIS в vault

| Файл | Назначение |
|------|------------|
| Log.md | Журнал |
| Inbox.md | Быстрый захват |
| Tasks.md | Задачи |
| Memory.md | Память ассистента |
| Architecture.md | Схема агентов |

## Работает сейчас

Статус, заметки, погода, задачи, время.
