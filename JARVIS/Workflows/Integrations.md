# Интеграции

| Интеграция | Статус | Примечание |
|---|---|---|
| Web cockpit | Работает локально | http://127.0.0.1:8765 |
| SQLite | Работает локально | `data/jarvis.db` |
| Obsidian Local REST API | Требует настройки | URL и ключ в локальном config/settings.json |
| Browser SpeechRecognition | Условно доступен | Chrome/Edge и поддержка браузера |
| OpenAI GPT | Не подключён | Нужна отдельная реализация и API key |
| Gmail / Google Calendar | Не подключены | Нужен OAuth |
| MCP | Планируется | Нужен allow-list и policy engine |
| sherpa-onnx / Piper | Заготовка | Нужны модели и runtime |
| n8n | Планируется | Отдельный локальный/облачный workflow-сервис |

Не указывай интеграцию как подключённую, пока не пройдена реальная проверка.
