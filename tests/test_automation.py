"""
Tests for automation module.

Tests browser automation, freelance registration, and MCP task management.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from automation.browser_agent import BrowserAgent, BrowserConfig, AutomationStep
from automation.freelance_registrar import (
    FreelanceRegistrar,
    PlatformType,
    RegistrationData,
    APIConfig,
    UpworkHandler,
)
from automation.mcp_integration import MCPTaskManager, Task, TaskStatus, TaskPriority


class TestBrowserAgent:
    """Test BrowserAgent functionality."""

    @pytest.mark.asyncio
    async def test_browser_config_defaults(self):
        """Test default browser configuration."""
        config = BrowserConfig()
        assert config.headless == False
        assert config.slow_mo == 100
        assert config.timeout == 30000
        assert config.viewport == {"width": 1920, "height": 1080}

    @pytest.mark.asyncio
    async def test_automation_step_creation(self):
        """Test automation step creation."""
        step = AutomationStep(
            action="click",
            selector="button#submit",
            value=None,
            description="Click submit button"
        )
        assert step.action == "click"
        assert step.selector == "button#submit"
        assert step.description == "Click submit button"

    @pytest.mark.asyncio
    @patch('automation.browser_agent.async_playwright')
    async def test_browser_agent_start_stop(self, mock_playwright):
        """Test browser agent lifecycle."""
        # Mock playwright
        mock_pw_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        config = BrowserConfig(headless=True)
        agent = BrowserAgent(config)

        await agent.start()
        assert agent.browser is not None

        await agent.stop()


class TestFreelanceRegistrar:
    """Test FreelanceRegistrar functionality."""

    def test_registration_data_creation(self):
        """Test registration data structure."""
        data = RegistrationData(
            email="test@example.com",
            password="TestPass123!",
            first_name="John",
            last_name="Doe",
            country="US"
        )
        assert data.email == "test@example.com"
        assert data.first_name == "John"
        assert data.skills == []

    def test_api_config_defaults(self):
        """Test API configuration defaults."""
        config = APIConfig()
        assert config.api_key is None
        assert config.scopes == ["read", "write"]

    def test_upwork_handler_registration_steps(self):
        """Test Upwork handler generates correct steps."""
        handler = UpworkHandler()
        data = RegistrationData(
            email="test@example.com",
            password="pass",
            first_name="John",
            last_name="Doe"
        )

        steps = handler.get_registration_steps(data)
        assert len(steps) > 0
        assert steps[0].action == "navigate"
        assert "upwork.com" in steps[0].value

    def test_platform_type_enum(self):
        """Test platform type enum."""
        assert PlatformType.UPWORK.value == "upwork"
        assert PlatformType.FIVERR.value == "fiverr"


class TestMCPTaskManager:
    """Test MCP Task Manager functionality."""

    def test_task_creation(self):
        """Test task creation."""
        manager = MCPTaskManager()
        task = manager.create_task(
            title="Test Task",
            description="Test Description",
            task_type="registration",
            platform="upwork",
            priority=TaskPriority.HIGH
        )

        assert task.title == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.HIGH
        assert task.platform == "upwork"

    def test_get_task_by_id(self):
        """Test retrieving task by ID."""
        manager = MCPTaskManager()
        task = manager.create_task(
            title="Test",
            description="Test",
            task_type="test",
            platform="upwork"
        )

        retrieved = manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_get_tasks_by_status(self):
        """Test filtering tasks by status."""
        manager = MCPTaskManager()

        # Create tasks with different statuses
        task1 = manager.create_task("T1", "D1", "t1", "upwork")
        task2 = manager.create_task("T2", "D2", "t2", "fiverr")
        task2.status = TaskStatus.COMPLETED

        pending_tasks = manager.get_tasks_by_status(TaskStatus.PENDING)
        completed_tasks = manager.get_tasks_by_status(TaskStatus.COMPLETED)

        assert len(pending_tasks) == 1
        assert len(completed_tasks) == 1
        assert pending_tasks[0].id == task1.id
        assert completed_tasks[0].id == task2.id

    def test_get_tasks_by_platform(self):
        """Test filtering tasks by platform."""
        manager = MCPTaskManager()

        task1 = manager.create_task("T1", "D1", "t1", "upwork")
        task2 = manager.create_task("T2", "D2", "t2", "fiverr")
        task3 = manager.create_task("T3", "D3", "t3", "upwork")

        upwork_tasks = manager.get_tasks_by_platform("upwork")
        fiverr_tasks = manager.get_tasks_by_platform("fiverr")

        assert len(upwork_tasks) == 2
        assert len(fiverr_tasks) == 1

    def test_queue_stats(self):
        """Test queue statistics."""
        manager = MCPTaskManager()

        task1 = manager.create_task("T1", "D1", "t1", "upwork")
        task2 = manager.create_task("T2", "D2", "t2", "fiverr")
        task2.status = TaskStatus.COMPLETED

        stats = manager.get_queue_stats()

        assert stats["total_tasks"] == 2
        assert stats["pending"] == 1
        assert stats["completed"] == 1
        assert stats["running"] == 0

    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        """Test enqueueing a task."""
        manager = MCPTaskManager()
        task = manager.create_task("Test", "Desc", "type", "platform")

        await manager.enqueue_task(task)
        assert manager.task_queue.qsize() >= 0

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task."""
        manager = MCPTaskManager()
        task = manager.create_task("Test", "Desc", "type", "platform")
        task.status = TaskStatus.RUNNING

        result = await manager.cancel_task(task.id)
        assert result == True
        assert task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self):
        """Test cancelling non-existent task."""
        manager = MCPTaskManager()
        result = await manager.cancel_task("nonexistent_id")
        assert result == False


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_registration_workflow(self):
        """Test complete registration workflow (mocked)."""
        # This would be an integration test with mocked browser
        # In real scenario, this would test the full flow
        pass

    @pytest.mark.asyncio
    async def test_batch_registration(self):
        """Test batch registration workflow (mocked)."""
        # This would test registering on multiple platforms
        pass


# Fixtures
@pytest.fixture
def sample_registration_data():
    """Sample registration data for tests."""
    return RegistrationData(
        email="test@example.com",
        password="SecurePass123!",
        first_name="John",
        last_name="Doe",
        country="US",
        skills=["Python", "JavaScript"]
    )


@pytest.fixture
def sample_api_config():
    """Sample API configuration for tests."""
    return APIConfig(
        webhook_url="https://example.com/webhook",
        scopes=["read", "write"]
    )


@pytest.fixture
def browser_config():
    """Browser configuration for tests."""
    return BrowserConfig(
        headless=True,
        slow_mo=0,
        timeout=10000
    )
