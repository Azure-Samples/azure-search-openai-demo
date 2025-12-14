# Автоматизация регистрации на фриланс-биржах

Этот модуль предоставляет автономную систему для автоматизации регистрации на фриланс-платформах с использованием RAG (Retrieval-Augmented Generation) системы и браузерной автоматизации.

## Возможности

- ✅ **Автоматическая регистрация** на платформах: Upwork, Fiverr, Freelancer и др.
- ✅ **Настройка API ключей** автоматически
- ✅ **Конфигурация вебхуков** для интеграции
- ✅ **RAG-powered интеллект** - использование Azure Search + OpenAI для принятия решений
- ✅ **MCP интеграция** - управление задачами через Model Context Protocol
- ✅ **Edge/Chromium поддержка** - работа с реальным браузером
- ✅ **Скриншоты и логи** - полная трассировка процесса
- ✅ **Retry логика** - автоматические повторы при ошибках

## Архитектура

```
automation/
├── __init__.py              # Точка входа модуля
├── browser_agent.py         # Автоматизация браузера (Playwright)
├── freelance_registrar.py   # Логика регистрации на платформах
├── mcp_integration.py       # Управление задачами через MCP
└── rag_agent.py            # RAG-интеграция для умных решений

external/
└── taskade-mcp/            # Taskade MCP library (клонирован)

data/
└── Freelance_Platform_Registration_Guide.md  # База знаний для RAG
```

## Установка

1. Установите зависимости:

```bash
cd app/backend
pip install -r requirements.txt
```

2. Установите браузеры Playwright:

```bash
playwright install
playwright install msedge  # Для Edge
```

3. Убедитесь, что RAG система настроена и работает.

## Использование

### 1. Через API

#### Получить список платформ

```bash
curl -X GET http://localhost:50505/automation/platforms \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Зарегистрироваться на платформе

```bash
curl -X POST http://localhost:50505/automation/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "platform": "upwork",
    "registration_data": {
      "email": "your@email.com",
      "password": "SecurePassword123!",
      "first_name": "John",
      "last_name": "Doe",
      "country": "US",
      "skills": ["Python", "JavaScript", "AI"]
    },
    "api_config": {
      "webhook_url": "https://your-domain.com/webhook"
    },
    "headless": false
  }'
```

#### Создать задачу автоматизации

```bash
curl -X POST http://localhost:50505/automation/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Register on Upwork",
    "description": "Complete registration with API setup",
    "task_type": "registration",
    "platform": "upwork",
    "priority": "high"
  }'
```

#### Просмотреть задачи

```bash
curl -X GET http://localhost:50505/automation/tasks \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Массовая регистрация

```bash
curl -X POST http://localhost:50505/automation/batch-register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "platforms": ["upwork", "fiverr", "freelancer"],
    "registration_data": {
      "email": "your@email.com",
      "password": "SecurePassword123!",
      "first_name": "John",
      "last_name": "Doe"
    },
    "api_config": {
      "webhook_url": "https://your-domain.com/webhook"
    }
  }'
```

### 2. Через Python код

```python
import asyncio
from automation import FreelanceRegistrar, PlatformType, RegistrationData, APIConfig, BrowserConfig

async def main():
    # Настройка данных для регистрации
    registration_data = RegistrationData(
        email="your@email.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe",
        country="US",
        skills=["Python", "JavaScript", "AI"]
    )

    # Настройка API
    api_config = APIConfig(
        webhook_url="https://your-domain.com/webhook",
        scopes=["read", "write"]
    )

    # Настройка браузера
    browser_config = BrowserConfig(
        headless=False,  # Видимый режим для отладки
        slow_mo=100      # Замедление для наблюдения
    )

    # Создаём регистратор
    registrar = FreelanceRegistrar(browser_config)

    # Запускаем регистрацию
    result = await registrar.register_platform(
        platform=PlatformType.UPWORK,
        registration_data=registration_data,
        api_config=api_config,
        setup_api=True,
        setup_webhooks=True
    )

    # Проверяем результат
    if result.success:
        print(f"✅ Успешно зарегистрирован на {result.platform}")
        print(f"📸 Скриншоты: {result.screenshots}")
        if result.api_config:
            print(f"🔑 API настроен")
    else:
        print(f"❌ Ошибка: {result.errors}")

asyncio.run(main())
```

### 3. С использованием MCP Task Manager

```python
import asyncio
from automation import MCPTaskManager, TaskPriority

async def main():
    # Создаём менеджер задач
    manager = MCPTaskManager()

    # Запускаем обработчик задач
    await manager.start_processor()

    # Создаём задачу
    task = manager.create_task(
        title="Register on Upwork",
        description="Full registration with API and webhooks",
        task_type="registration",
        platform="upwork",
        priority=TaskPriority.HIGH,
        metadata={
            "email": "your@email.com",
            "requires_api": True,
            "requires_webhooks": True
        }
    )

    # Добавляем в очередь
    await manager.enqueue_task(task)

    # Ждём завершения
    while task.status.value != "completed":
        await asyncio.sleep(1)
        stats = manager.get_queue_stats()
        print(f"Статус: {stats}")

    print(f"✅ Задача завершена: {task.result}")

asyncio.run(main())
```

## API Эндпоинты

### Platforms
- `GET /automation/platforms` - Список поддерживаемых платформ

### Registration
- `POST /automation/register` - Регистрация на одной платформе
- `POST /automation/batch-register` - Регистрация на нескольких платформах

### Tasks
- `POST /automation/tasks` - Создать задачу
- `GET /automation/tasks` - Список всех задач
- `GET /automation/tasks/<task_id>` - Получить задачу по ID
- `POST /automation/tasks/<task_id>/cancel` - Отменить задачу

### Stats
- `GET /automation/stats` - Статистика задач
- `GET /automation/health` - Health check

## Поддерживаемые платформы

### Полная поддержка
- ✅ **Upwork** - регистрация, API, webhooks
- ✅ **Fiverr** - регистрация (API ограничен)

### В разработке
- 🚧 **Freelancer.com** - регистрация, API
- 🚧 **Guru** - регистрация
- 🚧 **PeoplePerHour** - регистрация

### Добавление новой платформы

1. Создайте handler в `freelance_registrar.py`:

```python
class NewPlatformHandler(FreelancePlatformHandler):
    def __init__(self):
        super().__init__(PlatformType.NEW_PLATFORM)
        self.base_url = "https://newplatform.com"

    def get_registration_steps(self, data: RegistrationData) -> List[AutomationStep]:
        return [
            AutomationStep(
                action="navigate",
                value=f"{self.base_url}/signup",
                description="Navigate to signup"
            ),
            # ... добавьте шаги
        ]
```

2. Зарегистрируйте handler:

```python
FreelanceRegistrar.PLATFORM_HANDLERS[PlatformType.NEW_PLATFORM] = NewPlatformHandler
```

3. Добавьте документацию в `data/Freelance_Platform_Registration_Guide.md`

## RAG Интеграция

Система использует RAG для:
- Получения инструкций по регистрации из базы знаний
- Генерации automation steps через OpenAI
- Обучения на успешных/неуспешных попытках

База знаний находится в `data/Freelance_Platform_Registration_Guide.md`.

## Конфигурация

### Environment Variables

```bash
# Не требуется дополнительных переменных
# Использует существующую Azure OpenAI и Search конфигурацию
```

### Browser Configuration

```python
BrowserConfig(
    headless=True,          # Фоновый режим
    slow_mo=100,           # Замедление (мс)
    timeout=30000,         # Таймаут (мс)
    viewport={"width": 1920, "height": 1080},
    user_agent="Custom Agent"  # Опционально
)
```

## Безопасность

⚠️ **ВАЖНО**:

1. **Храните credentials безопасно** - используйте Azure Key Vault
2. **Проверяйте ToS платформ** - убедитесь что автоматизация разрешена
3. **Используйте 2FA** где возможно
4. **Ротируйте API ключи** регулярно
5. **Логируйте все действия**

## Troubleshooting

### Браузер не запускается

```bash
# Переустановите Playwright
playwright install --force

# Проверьте зависимости
playwright install-deps
```

### Селекторы не работают

Платформы часто меняют свои интерфейсы. Проверьте актуальность селекторов:

```python
# Включите режим отладки
browser_config = BrowserConfig(headless=False, slow_mo=500)

# Сделайте скриншоты
await agent.screenshot("debug.png")
```

### CAPTCHA блокирует регистрацию

1. Используйте сервисы решения CAPTCHA (2captcha, Anti-Captcha)
2. Добавьте ручной шаг для решения
3. Уменьшите частоту запросов

## Тестирование

```bash
# Запустите тесты
cd /workspaces/azure-search-openai-demo
pytest tests/test_automation.py -v

# С покрытием
pytest tests/test_automation.py --cov=app/backend/automation
```

## Примеры использования

### Scenario 1: Одиночная регистрация с мониторингом

```python
async def register_with_monitoring():
    registrar = FreelanceRegistrar()
    result = await registrar.register_platform(
        platform=PlatformType.UPWORK,
        registration_data=get_registration_data(),
        api_config=APIConfig(webhook_url="https://example.com/hook")
    )

    # Отправить уведомление
    if result.success:
        await send_notification("✅ Registration complete!")
        await save_credentials_to_vault(result.api_config)
    else:
        await send_alert(f"❌ Registration failed: {result.errors}")
```

### Scenario 2: Массовая регистрация с очередью

```python
async def batch_registration_with_queue():
    manager = MCPTaskManager()
    await manager.start_processor()

    platforms = [PlatformType.UPWORK, PlatformType.FIVERR]

    for platform in platforms:
        task = manager.create_task(
            title=f"Register on {platform.value}",
            description="Automated registration",
            task_type="registration",
            platform=platform.value,
            priority=TaskPriority.MEDIUM
        )
        await manager.enqueue_task(task)

    # Мониторинг прогресса
    while manager.get_queue_stats()["pending"] > 0:
        stats = manager.get_queue_stats()
        print(f"Progress: {stats['completed']}/{stats['total_tasks']}")
        await asyncio.sleep(5)
```

## Roadmap

- [ ] Поддержка больше платформ (LinkedIn, TopTal, etc.)
- [ ] Автоматическое решение CAPTCHA
- [ ] Интеграция с AI для адаптивных селекторов
- [ ] Dashboard для мониторинга задач
- [ ] Webhook notifications
- [ ] Rate limiting и anti-detection улучшения

## Contributing

См. [CONTRIBUTING.md](../../CONTRIBUTING.md)

## License

См. [LICENSE](../../LICENSE)

## Поддержка

Для вопросов и проблем создавайте issue в GitHub: https://github.com/Azure-Samples/azure-search-openai-demo/issues

---

**⚠️ Disclaimer**: Автоматизация регистрации должна соответствовать Terms of Service целевых платформ. Используйте на свой страх и риск.
