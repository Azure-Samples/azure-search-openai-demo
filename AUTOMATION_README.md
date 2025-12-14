# 🚀 Система Автоматизации Регистрации на Фриланс-Биржах

## Обзор

Комплексная система для автоматизированной регистрации на фриланс-платформах с использованием:
- ✅ **RAG (Retrieval-Augmented Generation)** - Azure Search + OpenAI для интеллектуальных решений
- ✅ **MCP (Model Context Protocol)** - управление задачами от Taskade
- ✅ **Playwright** - автоматизация браузера (Edge/Chromium)
- ✅ **REST API** - удобные эндпоинты для интеграции

## Быстрый старт

### 1. Установка зависимостей

```bash
# Backend зависимости
cd app/backend
pip install -r requirements.txt

# Установка Playwright
playwright install
playwright install msedge
```

### 2. Запуск примера

```bash
# Запустить демонстрационный скрипт
python examples/quickstart_automation.py
```

### 3. Использование API

```bash
# Запустить сервер (если еще не запущен)
cd app/backend
python -m quart run --reload -p 50505

# Зарегистрироваться на платформе
curl -X POST http://localhost:50505/automation/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "platform": "upwork",
    "registration_data": {
      "email": "your@email.com",
      "password": "SecurePass123!",
      "first_name": "John",
      "last_name": "Doe"
    }
  }'
```

## Структура проекта

```
app/backend/automation/
├── __init__.py              # Модуль инициализации
├── browser_agent.py         # Playwright автоматизация
├── freelance_registrar.py   # Регистрация на платформах
├── mcp_integration.py       # MCP task management
└── rag_agent.py            # RAG интеграция

app/backend/
└── automation_api.py        # REST API эндпоинты

data/
└── Freelance_Platform_Registration_Guide.md  # База знаний

docs/
└── automation_guide.md      # Подробная документация

examples/
└── quickstart_automation.py # Примеры использования

tests/
└── test_automation.py       # Тесты

external/
└── taskade-mcp/            # Taskade MCP библиотека
```

## Поддерживаемые платформы

| Платформа | Регистрация | API | Webhooks | Статус |
|-----------|-------------|-----|----------|--------|
| Upwork    | ✅ | ✅ | ✅ | Готово |
| Fiverr    | ✅ | ⚠️ | ❌ | Готово |
| Freelancer | 🚧 | 🚧 | 🚧 | В разработке |
| Guru      | 🚧 | 🚧 | ❌ | Планируется |

## API Эндпоинты

### Platforms
```http
GET /automation/platforms
```

### Registration
```http
POST /automation/register
POST /automation/batch-register
```

### Tasks
```http
POST /automation/tasks
GET /automation/tasks
GET /automation/tasks/<task_id>
POST /automation/tasks/<task_id>/cancel
```

### Stats
```http
GET /automation/stats
GET /automation/health
```

## Примеры использования

### Python API

```python
from automation import FreelanceRegistrar, PlatformType, RegistrationData

async def register():
    data = RegistrationData(
        email="user@example.com",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe"
    )

    registrar = FreelanceRegistrar()
    result = await registrar.register_platform(
        platform=PlatformType.UPWORK,
        registration_data=data
    )

    return result
```

### Task Management

```python
from automation import MCPTaskManager, TaskPriority

manager = MCPTaskManager()
await manager.start_processor()

task = manager.create_task(
    title="Register on Upwork",
    task_type="registration",
    platform="upwork",
    priority=TaskPriority.HIGH
)

await manager.enqueue_task(task)
```

## Конфигурация

### Browser Config

```python
from automation import BrowserConfig

config = BrowserConfig(
    headless=True,       # Фоновый режим
    slow_mo=100,        # Замедление (мс)
    timeout=30000       # Таймаут (мс)
)
```

### Environment Variables

Система использует существующую конфигурацию Azure:
- `AZURE_OPENAI_SERVICE`
- `AZURE_SEARCH_SERVICE`
- `AZURE_OPENAI_CHATGPT_DEPLOYMENT`

## Безопасность ⚠️

1. **Храните credentials в Azure Key Vault**
2. **Проверяйте Terms of Service платформ**
3. **Используйте 2FA где возможно**
4. **Ротируйте API ключи регулярно**
5. **Логируйте все операции**

## Тестирование

```bash
# Запустить тесты
pytest tests/test_automation.py -v

# С покрытием
pytest tests/test_automation.py --cov=app/backend/automation

# Конкретный тест
pytest tests/test_automation.py::TestBrowserAgent::test_browser_config_defaults -v
```

## Troubleshooting

### Браузер не запускается

```bash
playwright install --force
playwright install-deps
```

### Селекторы не работают

Включите debug mode:
```python
config = BrowserConfig(headless=False, slow_mo=500)
```

### CAPTCHA блокирует

1. Используйте сервисы решения CAPTCHA
2. Добавьте ручной шаг
3. Уменьшите частоту запросов

## Документация

- 📚 [Полное руководство](docs/automation_guide.md)
- 🏗️ [Архитектура RAG системы](docs/architecture.md)
- 🔧 [API документация](docs/http_protocol.md)
- 👨‍💻 [Для разработчиков](AGENTS.md)

## Roadmap

- [ ] Больше платформ (LinkedIn, TopTal)
- [ ] Автоматическое решение CAPTCHA
- [ ] AI-powered adaptive selectors
- [ ] Dashboard для мониторинга
- [ ] Webhook notifications
- [ ] Rate limiting improvements

## Contributing

См. [CONTRIBUTING.md](CONTRIBUTING.md)

## License

См. [LICENSE](LICENSE)

## Поддержка

Создавайте issues на GitHub:
https://github.com/Azure-Samples/azure-search-openai-demo/issues

---

**Создано с использованием:**
- Azure OpenAI
- Azure AI Search
- Playwright
- Taskade MCP
- Quart Framework

**⚠️ Disclaimer**: Убедитесь что автоматизация соответствует Terms of Service платформ. Используйте на свой риск.
