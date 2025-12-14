#!/bin/bash
# Быстрая установка и проверка системы автоматизации

set -e

echo "🚀 Установка системы автоматизации регистрации на фриланс-биржах"
echo "================================================================"

# 1. Установка Python зависимостей
echo ""
echo "📦 Шаг 1: Установка Python зависимостей..."
cd "$(dirname "$0")/../app/backend"
pip install -r requirements.txt

# 2. Установка Playwright
echo ""
echo "🎭 Шаг 2: Установка Playwright..."
playwright install chromium
playwright install msedge || echo "⚠️  Edge не найден, будет использован Chromium"

# 3. Проверка установки
echo ""
echo "✅ Шаг 3: Проверка установки..."
python -c "from automation import BrowserAgent; print('✓ Browser Agent')"
python -c "from automation import FreelanceRegistrar; print('✓ Freelance Registrar')"
python -c "from automation import MCPTaskManager; print('✓ MCP Task Manager')"

# 4. Запуск тестов
echo ""
echo "🧪 Шаг 4: Запуск тестов..."
cd ../..
pytest tests/test_automation.py -v --tb=short

# 5. Информация о следующих шагах
echo ""
echo "================================================================"
echo "✨ Установка завершена!"
echo ""
echo "📚 Следующие шаги:"
echo "  1. Изучите документацию: docs/automation_guide.md"
echo "  2. Запустите примеры: python examples/quickstart_automation.py"
echo "  3. Протестируйте API: curl http://localhost:50505/automation/health"
echo ""
echo "🔐 Безопасность:"
echo "  - Храните credentials в Azure Key Vault"
echo "  - Проверьте ToS платформ перед автоматизацией"
echo ""
echo "📖 Документация:"
echo "  - Полное руководство: docs/automation_guide.md"
echo "  - Архитектура: docs/automation_architecture.md"
echo "  - Краткий обзор: AUTOMATION_README.md"
echo ""
echo "Happy automating! 🎉"
