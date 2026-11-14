# JARVIS AI

Локальный персональный ассистент для Windows: веб-панель, задачи и долговременная память в SQLite, интеграция с Obsidian и модульная основа для голосовых и AI-функций.

## Быстрый запуск Windows

Требуется Python 3.10 или новее и Git.

1. Открой PowerShell в папке проекта.
2. Обнови проект по инструкции в разделе **Обновление существующей установки**.
3. Запусти:

```powershell
.\start.bat
```

4. Открой http://127.0.0.1:8765.

Окно терминала должно оставаться открытым. Для остановки нажми Ctrl+C.

Текущий запуск использует только стандартную библиотеку Python. Установка пакетов через pip для базового режима не требуется.

## Обновление существующей установки

Если в папке есть локальные изменения, сначала посмотри `git status -sb`. Не используй `git reset --hard` или `git clean` для обновления личного vault.

Для штатного обновления чистой рабочей копии:

```powershell
git pull --ff-only origin main
```

Если Git сообщает о локальных изменениях, остановись и сохрани их осознанно — не удаляй их командами очистки.

## Подключение локальной LLM и голосового режима

JARVIS использует локальный Ollama API — ключи и платная облачная подписка для этого режима не нужны.

1. Установи Ollama для Windows с официального сайта: https://ollama.com/download
2. Открой PowerShell и загрузи модель:

```powershell
ollama pull llama3.2
```

3. Убедись, что Ollama отвечает:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

4. В корне JARVIS включи провайдера в локальном конфиге, не заменяя остальные настройки:

```powershell
Set-Location "C:\Users\Admin\JARVIS"
if (!(Test-Path config\settings.json)) {
  Copy-Item config\settings.example.json config\settings.json
}
$config = Get-Content config\settings.json -Raw -Encoding UTF8 | ConvertFrom-Json
$config.llm | Add-Member -NotePropertyName provider -NotePropertyValue "ollama" -Force
$config.llm | Add-Member -NotePropertyName ollama_base -NotePropertyValue "http://127.0.0.1:11434" -Force
$config.llm | Add-Member -NotePropertyName model -NotePropertyValue "llama3.2" -Force
$config.llm | Add-Member -NotePropertyName timeout_seconds -NotePropertyValue 45 -Force
$config | ConvertTo-Json -Depth 20 | Set-Content config\settings.json -Encoding UTF8
```

5. Перезапусти JARVIS. В разделе **Integrations** состояние Ollama должно стать ONLINE. Если модель не скачана, панель покажет MODEL NOT DOWNLOADED.

### Голос без повторных нажатий

Открой JARVIS в актуальном Chrome или Edge, нажми значок микрофона один раз и разреши доступ к микрофону. После этого можно произносить «Джарвис, добавь задачу купить продукты» или сначала сказать «Джарвис», дождаться ответа «Слушаю», затем произнести команду. JARVIS озвучит ответ и снова включит ожидание ключевого слова.

Это hands-free режим вкладки браузера, а не системный фоновый wake-word сервис: браузер может приостанавливать распознавание в фоне, после блокировки Windows или при потере разрешения микрофона. Для постоянного прослушивания вне браузера потребуется отдельный локальный Windows-служебный модуль с офлайн-распознаванием. Произвольные команды PowerShell/CMD не исполняются; действия ограничены явно реализованными командами JARVIS.

## Что работает в текущей версии

- Веб-панель с тёмной темой.
- Локальный HTTP-сервер на `127.0.0.1:8765`.
- Проверка состояния ядра и Obsidian.
- Создание, просмотр, завершение и удаление задач.
- Сохранение и просмотр записей долговременной памяти.
- SQLite-хранилище в `data/jarvis.db`.
- Командный маршрутизатор: статус, заметки, поиск, погода, задачи, дата/время и помощь.
- Голосовой ввод браузера в Chrome/Edge, если SpeechRecognition доступен.
- Чтение, поиск и запись заметок через Obsidian Local REST API.

## Подключение Obsidian — без дополнительных плагинов

**Рабочий vault JARVIS — это папка `C:\Users\Admin\JARVIS\JARVIS`.** Не открывай как рабочий vault корень репозитория и не выбирай старую папку `obsidian-vault`: там лежит документация проекта, а не актуальная база заметок.

1. В Obsidian выбери **Open another vault → Open folder as vault**.
2. Укажи папку `C:\Users\Admin\JARVIS\JARVIS`.
3. Открой заметку `00 - Home.md`. Из неё доступны Inbox, Tasks, Memory, Log, Projects и Workflows.
4. В корне репозитория проверь локальную конфигурацию:

```powershell
if (!(Test-Path config\settings.json)) {
  Copy-Item config\settings.example.json config\settings.json
}
notepad config\settings.json
```

5. В секции `obsidian` должны быть значения:

```json
"mode": "filesystem",
"filesystem": { "vault_path": "JARVIS" }
```

Путь `JARVIS` разрешается относительно корня проекта. Сохрани настройки и перезапусти JARVIS. Веб-панель должна показать, что Obsidian подключён.

### Дополнительный вариант: Obsidian Local REST API

REST API не требуется для базового подключения через файловую систему. Его можно настроить отдельно, если понадобится работа через плагин Obsidian: установи **Local REST API**, укажи `mode = rest`, URL и API key в локальном `config/settings.json`.

**Никогда не отправляй API key в чат, не помещай его в заметки и не загружай в GitHub.** Файл `config/settings.json`, база данных и локальные настройки Obsidian исключены из Git. Не публикуй порт REST API или JARVIS в интернете.

## Структура Obsidian

В корне репозитория находится каталог `JARVIS/` с рабочими заметками:

- `00 - Home.md` — домашняя панель и навигация.
- `Log.md` — журнал действий и событий.
- `Inbox.md` — быстрый захват идей.
- `Tasks.md` — задачи в формате Obsidian checklist.
- `Memory.md` — долговременные заметки и факты.
- `Projects/` — проекты.
- `Workflows/` — сценарии и инструкции.
- `Templates/` — шаблоны заметок.

Папки `inbox/`, `memory/`, `tasks/` в корне, а также `.obsidian/` — личные локальные данные пользователя; они не синхронизируются в публичный GitHub. Операционная память и задачи интерфейса JARVIS отдельно хранятся в локальной SQLite базе.

## Ограничения текущей версии

- Свободный GPT-диалог ещё не подключён к текущему серверу `start.bat`. Поле чата пока обрабатывает поддерживаемые команды и возвращает подсказку для неизвестных запросов.
- OpenAI API, Gmail, Google Calendar, социальные сети и полноценный MCP-клиент не подключены.
- Голосовой ввод использует браузерный SpeechRecognition. Офлайн-движки sherpa-onnx и Piper пока являются заготовкой.
- Автоматизация браузера и рабочего стола, выполнение shell-команд, финансовые операции и удалённый доступ отключены.

## Разработка и проверка

Из корня репозитория:

```powershell
python -m compileall backend
python -m unittest discover -s tests -v
python backend\server.py
```

Проверка API после запуска:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health
Invoke-RestMethod http://127.0.0.1:8765/api/tasks
Invoke-RestMethod http://127.0.0.1:8765/api/memory
```

## Безопасность

- Сервис отказывается запускаться на внешнем сетевом интерфейсе.
- Секреты и локальная база не коммитятся.
- Неизвестные инструменты запрещены по умолчанию.
- Внешние действия требуют отдельного подтверждения.
- Не включай удалённый доступ без аутентификации, TLS, защиты от CSRF, ограничения запросов и аудита.
