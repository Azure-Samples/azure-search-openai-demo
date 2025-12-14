"""Tests for Taskade integration"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "app" / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from automation import TaskadeClient, TaskadeConfig


def test_taskade_config():
    """Test TaskadeConfig creation"""
    config = TaskadeConfig(api_key="test_key")
    assert config.api_key == "test_key"
    assert config.base_url == "https://www.taskade.com/api/v1"
    assert config.timeout == 30


def test_taskade_client_init():
    """Test TaskadeClient initialization"""
    config = TaskadeConfig(api_key="test_key")
    client = TaskadeClient(config)
    assert client.config.api_key == "test_key"
    assert client.session is None


@pytest.mark.asyncio
async def test_taskade_client_context_manager():
    """Test TaskadeClient as async context manager"""
    config = TaskadeConfig(api_key="tskdp_test")

    async with TaskadeClient(config) as client:
        assert client.session is not None


def test_imports():
    """Test that all expected classes can be imported"""
    from automation import (
        TaskadeClient,
        TaskadeConfig,
        TaskadeFreelanceIntegration,
        Workspace,
        Project,
        Task,
    )

    assert TaskadeClient is not None
    assert TaskadeConfig is not None
    assert TaskadeFreelanceIntegration is not None
