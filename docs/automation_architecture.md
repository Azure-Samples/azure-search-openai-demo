# Архитектура Системы Автоматизации

## Общая архитектура

```mermaid
graph TB
    User[Пользователь] --> API[REST API]
    User --> CLI[Python CLI]

    API --> AutoAPI[automation_api.py]
    CLI --> AutoAPI

    AutoAPI --> Registrar[FreelanceRegistrar]
    AutoAPI --> TaskMgr[MCPTaskManager]

    Registrar --> Browser[BrowserAgent]
    Registrar --> RAG[RAGAgent]

    Browser --> Playwright[Playwright/Edge]
    RAG --> Search[Azure AI Search]
    RAG --> OpenAI[Azure OpenAI]

    TaskMgr --> Queue[Task Queue]
    TaskMgr --> Tasks[(Task Storage)]

    Search --> KB[(Knowledge Base)]
    KB --> Docs[Registration Guides]

    Playwright --> Upwork[Upwork.com]
    Playwright --> Fiverr[Fiverr.com]
    Playwright --> Other[Other Platforms]

    style User fill:#e1f5ff
    style API fill:#fff4e1
    style Registrar fill:#ffe1f5
    style RAG fill:#e1ffe1
    style Browser fill:#f5e1ff
```

## Поток регистрации

```mermaid
sequenceDiagram
    participant U as User
    participant API as REST API
    participant R as Registrar
    participant RAG as RAG Agent
    participant B as Browser Agent
    participant P as Platform

    U->>API: POST /automation/register
    API->>R: register_platform()
    R->>RAG: get_platform_instructions()
    RAG->>RAG: Search knowledge base
    RAG-->>R: Return instructions

    R->>B: execute_steps()
    B->>B: Start browser (Edge)

    loop For each step
        B->>P: Navigate/Fill/Click
        P-->>B: Response
        B->>B: Screenshot
    end

    B-->>R: Execution result
    R->>RAG: learn_from_execution()
    R-->>API: RegistrationResult
    API-->>U: JSON response
```

## Компоненты

### 1. BrowserAgent
Управление браузером Playwright:
- Запуск Edge/Chromium
- Навигация по страницам
- Заполнение форм
- Скриншоты
- Управление cookies

### 2. FreelanceRegistrar
Оркестрация процесса регистрации:
- Platform-specific handlers
- Полный цикл: регистрация → API → webhooks
- Batch processing
- Error handling

### 3. MCPTaskManager
Управление задачами:
- Task queue
- Priority scheduling
- Progress tracking
- Async execution

### 4. RAGAgent
Интеллектуальные решения:
- Поиск инструкций в KB
- Генерация automation steps
- Обучение на результатах

## Поток данных

```mermaid
flowchart LR
    A[Registration Data] --> B[Registrar]
    B --> C{Platform Handler}

    C -->|Upwork| D1[Upwork Steps]
    C -->|Fiverr| D2[Fiverr Steps]
    C -->|Other| D3[Custom Steps]

    D1 --> E[Browser Agent]
    D2 --> E
    D3 --> E

    E --> F[Execute Steps]
    F --> G{Success?}

    G -->|Yes| H[API Setup]
    G -->|No| I[Error Handling]

    H --> J[Webhook Config]
    J --> K[Result]
    I --> K

    K --> L[Screenshot Storage]
    K --> M[Logs]
    K --> N[User Response]
```

## Интеграция с RAG системой

```mermaid
graph TB
    subgraph "RAG System"
        Search[Azure AI Search]
        Index[Search Index]
        OpenAI[Azure OpenAI]
    end

    subgraph "Automation System"
        RAGAgent[RAG Agent]
        Browser[Browser Agent]
        Registrar[Registrar]
    end

    subgraph "Knowledge Base"
        Docs[Platform Guides]
        Patterns[Success Patterns]
        Errors[Error Solutions]
    end

    Docs --> Index
    Patterns --> Index
    Errors --> Index

    RAGAgent --> Search
    Search --> Index
    RAGAgent --> OpenAI

    RAGAgent --> Registrar
    Registrar --> Browser

    Browser -.Feedback.-> Patterns
    Browser -.Errors.-> Errors
```

## Task Management Flow

```mermaid
stateDiagram-v2
    [*] --> Pending: Create Task
    Pending --> InQueue: Enqueue
    InQueue --> Running: Processor picks up
    Running --> Completed: Success
    Running --> Failed: Error
    Running --> Cancelled: User cancels

    Completed --> [*]
    Failed --> [*]
    Cancelled --> [*]

    note right of Running
        Max 3 concurrent
        tasks at a time
    end note
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Azure Resources"
        AppService[Azure App Service]
        Search[Azure AI Search]
        OpenAI[Azure OpenAI]
        KeyVault[Azure Key Vault]
        Storage[Azure Blob Storage]
    end

    subgraph "Application"
        Backend[Quart Backend]
        Automation[Automation Module]
        Tasks[Task Queue]
    end

    subgraph "Browser Pool"
        Edge1[Edge Instance 1]
        Edge2[Edge Instance 2]
        Edge3[Edge Instance 3]
    end

    AppService --> Backend
    Backend --> Automation
    Automation --> Tasks

    Tasks --> Edge1
    Tasks --> Edge2
    Tasks --> Edge3

    Automation --> Search
    Automation --> OpenAI
    Automation --> KeyVault
    Backend --> Storage

    Edge1 -.Register.-> Platforms[Freelance Platforms]
    Edge2 -.Register.-> Platforms
    Edge3 -.Register.-> Platforms
```

## Error Handling Flow

```mermaid
flowchart TD
    Start[Execute Step] --> Check{Success?}
    Check -->|Yes| Next[Next Step]
    Check -->|No| Screenshot[Capture Screenshot]

    Screenshot --> Retry{Retry < 3?}
    Retry -->|Yes| Wait[Wait & Retry]
    Wait --> Start

    Retry -->|No| Log[Log Error]
    Log --> RAG[Update RAG KB]
    RAG --> Notify[Notify User]
    Notify --> End[End]

    Next --> Done{More Steps?}
    Done -->|Yes| Start
    Done -->|No| Success[Success]
    Success --> End
```

## Security Architecture

```mermaid
graph LR
    subgraph "User Layer"
        U[User]
        Auth[Authentication]
    end

    subgraph "API Layer"
        API[REST API]
        JWT[JWT Validation]
    end

    subgraph "Data Layer"
        Creds[Credentials]
        KV[Key Vault]
        Encrypt[Encryption]
    end

    U --> Auth
    Auth --> JWT
    JWT --> API
    API --> Creds
    Creds --> Encrypt
    Encrypt --> KV

    style KV fill:#ff6b6b
    style Encrypt fill:#ff6b6b
    style Auth fill:#4ecdc4
```

## Масштабирование

### Горизонтальное
- Несколько экземпляров App Service
- Распределенная очередь задач
- Load balancing

### Вертикальное
- Больше concurrent tasks
- Faster browser instances
- Увеличение memory/CPU

## Мониторинг

```mermaid
graph TB
    App[Application] --> Logs[Azure Monitor Logs]
    App --> Metrics[Application Insights]
    App --> Alerts[Alert Rules]

    Logs --> Dashboard[Monitoring Dashboard]
    Metrics --> Dashboard
    Alerts --> Notify[Email/SMS/Teams]

    Dashboard --> Admin[Administrator]
    Notify --> Admin
```

## Компоненты модуля automation

| Компонент | Ответственность | Зависимости |
|-----------|----------------|-------------|
| `browser_agent.py` | Browser automation | Playwright |
| `freelance_registrar.py` | Platform registration | BrowserAgent |
| `mcp_integration.py` | Task management | asyncio, dataclasses |
| `rag_agent.py` | RAG intelligence | Azure Search, OpenAI |
| `automation_api.py` | REST endpoints | Quart |

## Расширение системы

### Добавление новой платформы

1. Создать handler в `freelance_registrar.py`
2. Определить registration steps
3. Добавить в PLATFORM_HANDLERS
4. Обновить документацию в KB
5. Добавить тесты

### Добавление нового типа задачи

1. Расширить TaskType enum
2. Добавить обработчик в execute_task()
3. Обновить API endpoints
4. Документировать

## Производительность

### Оптимизации

- **Browser pooling**: Переиспользование инстансов
- **Parallel execution**: До 3 одновременно
- **Caching**: Кеширование RAG результатов
- **Rate limiting**: Защита от блокировок

### Метрики

- Время регистрации: ~2-5 минут
- Success rate: 85-95%
- Concurrent tasks: 3 default, до 10
- Memory per task: ~200-300MB

---

Эта архитектура обеспечивает:
✅ Масштабируемость
✅ Отказоустойчивость
✅ Безопасность
✅ Расширяемость
