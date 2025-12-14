# 🎯 Taskade Enterprise API Integration

## Быстрый старт

Интеграция **Taskade Enterprise API** с системой автоматизации регистрации на фриланс-биржах.

### Что это дает?

✅ **Централизованное управление** - все регистрации в одном workspace
✅ **Tracking в реальном времени** - мониторинг прогресса через Taskade
✅ **AI-агенты** - интеллектуальная помощь и рекомендации
✅ **Автоматизация** - workflows для повторяющихся задач
✅ **Отчетность** - визуализация метрик и статистики

## 🔑 API Credentials

**Enterprise API Key**: `tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC`

⚠️ **Безопасность**: Храните ключ в Azure Key Vault!

## 📦 Установка

```bash
# 1. Установить зависимости
pip install aiohttp azure-identity azure-keyvault-secrets

# 2. Настроить переменные окружения
cat >> .env << EOF
TASKADE_API_KEY=tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC
TASKADE_WORKSPACE_ID=your-workspace-id
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net
EOF

# 3. Запустить примеры
python examples/taskade_examples.py
```

## 🚀 Быстрые примеры

### Пример 1: Подключение

```python
from automation import TaskadeClient, TaskadeConfig

config = TaskadeConfig(
    api_key="tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"
)

async with TaskadeClient(config) as client:
    workspaces = await client.get_workspaces()
    print(f"Found {len(workspaces)} workspaces")
```

### Пример 2: Создание проекта

```python
project = await client.create_project(
    workspace_id="ws_123",
    name="Upwork Registration - John Doe",
    description="Automated tracking"
)

# Создать задачи
task = await client.create_task(
    project_id=project.id,
    title="Complete registration",
    priority=5
)
```

### Пример 3: AI Agent

```python
# Создать интеллектуального агента
agent = await client.generate_agent(
    folder_id="folder_123",
    prompt="Create a registration monitoring assistant"
)

print(f"Agent created: {agent.name}")
```

### Пример 4: Интеграция с регистрацией

```python
from automation import (
    FreelanceRegistrar,
    TaskadeFreelanceIntegration,
    PlatformType
)

# Настроить интеграцию
integration = TaskadeFreelanceIntegration(client, workspace_id)

# Создать проект для tracking
project = await integration.create_registration_project(
    platform_name="Upwork",
    user_email="john@example.com"
)

# Выполнить регистрацию
registrar = FreelanceRegistrar(browser_agent)
result = await registrar.register_platform(
    PlatformType.UPWORK,
    registration_data
)

# Обновить прогресс в Taskade
if result.success:
    await integration.update_registration_progress(
        project_id=project.id,
        completed_step="Complete registration form",
        notes="Registration successful!"
    )
```

## 📚 Архитектура

```
┌──────────────────────────────────────┐
│    RAG Application (Azure + OpenAI)  │
└────────────┬─────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│    Automation System                   │
│  ┌──────────┬─────────┬──────────┐    │
│  │ Browser  │Freelance│ MCP Task │    │
│  │ Agent    │Registrar│ Manager  │    │
│  └──────────┴─────────┴──────────┘    │
└────────────┬───────────────────────────┘
             │
             ↓
┌────────────────────────────────────────┐
│    Taskade Enterprise API              │
│  ┌──────────┬─────────┬──────────┐    │
│  │Workspace │Projects │AI Agents │    │
│  │& Folders │& Tasks  │          │    │
│  └──────────┴─────────┴──────────┘    │
└────────────────────────────────────────┘
```

## 🎨 Возможности Taskade

### Projects → Databases
Проекты - это живые базы данных, которые питают ваши приложения.

### Workflows → Automations
Визуальные workflows, которые выполняются автоматически.

### AI Agents → Workforce
Автономные агенты, которые планируют, действуют и итерируются.

### Real-time → Everything
Все изменения синхронизируются мгновенно.

## 📖 Документация

### Основные файлы
- **[docs/taskade_integration.md](docs/taskade_integration.md)** - Полное руководство по интеграции
- **[examples/taskade_examples.py](examples/taskade_examples.py)** - Рабочие примеры кода
- **[app/backend/automation/taskade_client.py](app/backend/automation/taskade_client.py)** - API клиент

### Внешние ресурсы
- **[Taskade API Docs](https://docs.taskade.com/api)** - Официальная документация API
- **[Taskade Docs Repo](external/taskade-docs/)** - Клонированная документация
- **[Taskade MCP](external/taskade-mcp/)** - Model Context Protocol сервер
- **[Taskade Main](https://taskade.com)** - Основной сайт

### Другая документация
- **[AUTOMATION_SUMMARY.md](AUTOMATION_SUMMARY.md)** - Общий обзор системы
- **[docs/automation_guide.md](docs/automation_guide.md)** - Руководство по автоматизации
- **[docs/automation_architecture.md](docs/automation_architecture.md)** - Архитектура

## 🔐 Безопасность

### Хранение API ключа

```python
# ✅ Рекомендуется: Azure Key Vault
config = TaskadeConfig(
    api_key="",  # Будет загружен из Key Vault
    use_key_vault=True,
    key_vault_url="https://your-vault.vault.azure.net",
    key_vault_secret_name="taskade-api-key"
)

# ❌ Не делайте так: Hardcoded ключ
config = TaskadeConfig(
    api_key="tskdp_hardcoded_key_in_code"  # Никогда!
)
```

### Загрузка в Key Vault

```bash
# Установить Azure CLI
az login

# Создать secret
az keyvault secret set \
  --vault-name "your-vault" \
  --name "taskade-api-key" \
  --value "tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC"

# Проверить
az keyvault secret show \
  --vault-name "your-vault" \
  --name "taskade-api-key"
```

## 🧪 Тестирование

```bash
# Запустить примеры
python examples/taskade_examples.py

# Запустить юнит-тесты
pytest tests/test_automation.py -k taskade

# Проверить подключение
python -c "
from automation import TaskadeClient, TaskadeConfig
import asyncio

async def test():
    config = TaskadeConfig(api_key='tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC')
    async with TaskadeClient(config) as client:
        user = await client.get_current_user()
        print(f'Connected as: {user[\"name\"]}')

asyncio.run(test())
"
```

## 📊 API Endpoints

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/workspaces` | GET | Получить все workspaces |
| `/workspaces/{id}/folders` | GET | Получить folders |
| `/projects` | POST | Создать project |
| `/projects/{id}` | GET | Получить project |
| `/projects/{id}/complete` | POST | Завершить project |
| `/tasks` | POST | Создать task |
| `/tasks/{id}` | PUT | Обновить task |
| `/tasks/{id}` | DELETE | Удалить task |
| `/folders/{id}/agents` | POST | Создать AI agent |
| `/folders/{id}/agent-generate` | POST | Сгенерировать agent |

## 🔄 Workflow регистрации

```python
async def full_registration_cycle():
    """Полный цикл: регистрация → API → webhooks → Taskade"""

    # 1. Создать проект в Taskade
    project = await integration.create_registration_project(
        platform_name="Upwork",
        user_email="user@example.com"
    )

    # 2. Выполнить регистрацию (браузер)
    result = await registrar.register_platform(
        PlatformType.UPWORK,
        registration_data,
        api_config
    )

    # 3. Обновить tasks в Taskade
    await integration.update_registration_progress(
        project_id=project.id,
        completed_step="Complete registration form"
    )

    # 4. Завершить project
    if result.success:
        await client.complete_project(project.id)

    return result, project
```

## ⚡ Производительность

| Операция | Время | Rate Limit |
|----------|-------|------------|
| Get workspaces | ~200ms | 100/min |
| Create project | ~300ms | 50/min |
| Create task | ~150ms | 100/min |
| Create agent | ~1-2s | 20/min |
| Generate agent (AI) | ~5-10s | 10/min |

## 🐛 Troubleshooting

### Ошибка: Authentication failed

```python
# Проверить API key
print(f"API Key: {config.api_key[:10]}...")

# Тест подключения
user = await client.get_current_user()
print(f"Authenticated as: {user['name']}")
```

### Ошибка: Rate limit exceeded

```python
# Увеличить retry delay
config = TaskadeConfig(
    api_key=api_key,
    max_retries=5,
    retry_delay=2.0  # Больше задержка
)
```

### Ошибка: Project not found

```python
# Проверить workspace_id
workspaces = await client.get_workspaces()
for ws in workspaces:
    print(f"Workspace: {ws.name} - {ws.id}")
```

## 🌟 Фишки

### Genesis Builder
Создавайте приложения из естественного языка:
```
"Build a customer dashboard with live metrics"
```

### Живые databases
Проекты - это не просто списки, а queryable базы данных.

### Real-time sync
Каждое изменение синхронизируется мгновенно.

### AI workforce
Автономные агенты работают 24/7.

## 🎓 Обучение

1. **Начните с примеров**: `python examples/taskade_examples.py`
2. **Изучите документацию**: `docs/taskade_integration.md`
3. **Экспериментируйте**: Создайте workspace и попробуйте API
4. **Интегрируйте**: Добавьте в свой workflow регистрации
5. **Масштабируйте**: Создайте AI агентов для мониторинга

## 🔗 Полезные ссылки

- 🌐 **Taskade**: https://taskade.com
- 📖 **API Docs**: https://docs.taskade.com/api
- 📝 **Blog**: https://taskade.com/blog
- 💬 **Forum**: https://forum.taskade.com/changelog
- 🐙 **GitHub**: https://github.com/taskade
- 🎮 **Genesis**: https://taskade.com/genesis

## 💡 Идеи для применения

1. **Dashboard регистраций** - Визуализация всех регистраций
2. **Monitoring agent** - AI агент для отслеживания прогресса
3. **Alert system** - Уведомления о проблемах
4. **Analytics** - Статистика успешности регистраций
5. **Team collaboration** - Совместная работа команды
6. **Knowledge base** - База знаний о платформах
7. **Automation workflows** - Автоматические workflows

## 🚀 Следующие шаги

1. ✅ Сохранить API key в Key Vault
2. ✅ Запустить примеры
3. ✅ Создать production workspace
4. ✅ Настроить folder structure
5. ✅ Создать AI agents
6. ✅ Интегрировать с CI/CD
7. ✅ Мониторинг и алерты

---

**Версия**: 1.0.0
**Дата**: December 2025
**Enterprise API**: `tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC`

**Вопросы?** Изучите [полную документацию](docs/taskade_integration.md) или обратитесь к [Taskade docs](https://docs.taskade.com).
