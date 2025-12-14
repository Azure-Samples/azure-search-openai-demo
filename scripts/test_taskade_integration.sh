#!/bin/bash
# Быстрый тест Taskade интеграции

set -e

echo "🎯 Тестирование Taskade Enterprise API Integration"
echo "=" | tr '=' '=' | head -c 60 && echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка API ключа
API_KEY="${TASKADE_API_KEY:-tskdp_NvhoURdQXa1eDDxnCWrZYtb7k4uU2ZkHEC}"

echo -e "\n${YELLOW}📌 Используется API Key: ${API_KEY:0:20}...${NC}"

# Тест 1: Проверка подключения
echo -e "\n${YELLOW}Тест 1: Проверка подключения к Taskade API${NC}"

python3 << EOF
import asyncio
import sys
sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')

from automation import TaskadeClient, TaskadeConfig, TaskadeAPIError

async def test_connection():
    config = TaskadeConfig(api_key="$API_KEY")

    try:
        async with TaskadeClient(config) as client:
            user = await client.get_current_user()
            print(f"✅ Подключено как: {user.get('name', 'Unknown')}")
            print(f"   Email: {user.get('email', 'N/A')}")
            return True
    except TaskadeAPIError as e:
        print(f"❌ Ошибка API: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Тест 1 пройден${NC}"
else
    echo -e "${RED}❌ Тест 1 провален${NC}"
    exit 1
fi

# Тест 2: Получение workspaces
echo -e "\n${YELLOW}Тест 2: Получение workspaces${NC}"

python3 << EOF
import asyncio
import sys
sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')

from automation import TaskadeClient, TaskadeConfig

async def test_workspaces():
    config = TaskadeConfig(api_key="$API_KEY")

    try:
        async with TaskadeClient(config) as client:
            workspaces = await client.get_workspaces()
            print(f"✅ Найдено workspaces: {len(workspaces)}")

            for ws in workspaces:
                print(f"   - {ws.name} (ID: {ws.id})")
                print(f"     Members: {len(ws.members)}")

            return len(workspaces) > 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

result = asyncio.run(test_workspaces())
sys.exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Тест 2 пройден${NC}"
else
    echo -e "${RED}❌ Тест 2 провален${NC}"
    exit 1
fi

# Тест 3: Создание тестового проекта
echo -e "\n${YELLOW}Тест 3: Создание тестового проекта${NC}"

python3 << EOF
import asyncio
import sys
from datetime import datetime
sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')

from automation import TaskadeClient, TaskadeConfig

async def test_project_creation():
    config = TaskadeConfig(api_key="$API_KEY")

    try:
        async with TaskadeClient(config) as client:
            # Получить workspace
            workspaces = await client.get_workspaces()
            if not workspaces:
                print("❌ Нет доступных workspaces")
                return False

            workspace_id = workspaces[0].id

            # Создать проект
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project = await client.create_project(
                workspace_id=workspace_id,
                name=f"Test Project {timestamp}",
                description="Автоматический тест интеграции"
            )

            print(f"✅ Проект создан: {project.name}")
            print(f"   ID: {project.id}")

            # Создать задачу
            task = await client.create_task(
                project_id=project.id,
                title="Тестовая задача",
                description="Проверка создания задач",
                priority=3
            )

            print(f"✅ Задача создана: {task.title}")
            print(f"   ID: {task.id}")

            # Удалить тестовую задачу
            await client.delete_task(task.id)
            print(f"✅ Задача удалена")

            return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_project_creation())
sys.exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Тест 3 пройден${NC}"
else
    echo -e "${RED}❌ Тест 3 провален (возможно, нужны права на создание проектов)${NC}"
fi

# Тест 4: Интеграция с FreelanceRegistrar
echo -e "\n${YELLOW}Тест 4: Интеграция с FreelanceRegistrar${NC}"

python3 << EOF
import asyncio
import sys
sys.path.insert(0, '/workspaces/azure-search-openai-demo/app/backend')

from automation import (
    TaskadeClient,
    TaskadeConfig,
    TaskadeFreelanceIntegration
)

async def test_integration():
    config = TaskadeConfig(api_key="$API_KEY")

    try:
        async with TaskadeClient(config) as client:
            # Получить workspace
            workspaces = await client.get_workspaces()
            if not workspaces:
                print("❌ Нет доступных workspaces")
                return False

            workspace_id = workspaces[0].id

            # Создать интеграцию
            integration = TaskadeFreelanceIntegration(client, workspace_id)

            print(f"✅ Интеграция создана для workspace: {workspaces[0].name}")

            # Попробовать создать регистрационный проект
            project = await integration.create_registration_project(
                platform_name="Upwork (Test)",
                user_email="test@example.com"
            )

            print(f"✅ Регистрационный проект создан: {project.name}")
            print(f"   Tasks: {len(project.tasks) if hasattr(project, 'tasks') else 'Будут созданы'}")

            return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_integration())
sys.exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Тест 4 пройден${NC}"
else
    echo -e "${RED}❌ Тест 4 провален${NC}"
fi

# Итоговый отчет
echo -e "\n${'='*60}"
echo -e "${GREEN}✅ ВСЕ БАЗОВЫЕ ТЕСТЫ ЗАВЕРШЕНЫ!${NC}"
echo -e "${'='*60}"

echo -e "\n${YELLOW}📚 Следующие шаги:${NC}"
echo "  1. Сохраните API key в Azure Key Vault"
echo "  2. Запустите полные примеры: python examples/taskade_examples.py"
echo "  3. Изучите документацию: docs/taskade_integration.md"
echo "  4. Интегрируйте с вашими workflows"

echo -e "\n${YELLOW}📖 Документация:${NC}"
echo "  - TASKADE_README.md - Быстрый старт"
echo "  - docs/taskade_integration.md - Полное руководство"
echo "  - TASKADE_INTEGRATION_SUMMARY.md - Итоговый summary"

echo -e "\n${GREEN}Happy automating! 🚀${NC}"
