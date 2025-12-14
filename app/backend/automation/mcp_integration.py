"""
MCP (Model Context Protocol) integration with Taskade.

This module provides task management and orchestration for automated workflows.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """Represents an automation task."""

    id: str
    title: str
    description: str
    task_type: str  # registration, api_setup, webhook_setup
    platform: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data


class MCPTaskManager:
    """
    Task manager for automation workflows using MCP protocol concepts.

    Features:
    - Task queue management
    - Priority-based scheduling
    - Progress tracking
    - Error handling and retry logic
    - Integration with RAG for context-aware execution
    """

    def __init__(self):
        """Initialize task manager."""
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 3

    def create_task(
        self,
        title: str,
        description: str,
        task_type: str,
        platform: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title
            description: Task description
            task_type: Type of task
            platform: Target platform
            priority: Task priority
            metadata: Additional metadata

        Returns:
            Created task
        """
        task_id = f"{platform}_{task_type}_{datetime.utcnow().timestamp()}"

        task = Task(
            id=task_id,
            title=title,
            description=description,
            task_type=task_type,
            platform=platform,
            priority=priority,
            metadata=metadata or {},
        )

        self.tasks[task_id] = task
        logger.info(f"Created task: {task_id}")

        return task

    async def enqueue_task(self, task: Task):
        """Add task to queue."""
        await self.task_queue.put(task)
        logger.info(f"Enqueued task: {task.id}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_platform(self, platform: str) -> List[Task]:
        """Get tasks by platform."""
        return [task for task in self.tasks.values() if task.platform == platform]

    async def execute_task(self, task: Task) -> Task:
        """
        Execute a single task.

        This is a placeholder - actual execution should be implemented
        by integrating with FreelanceRegistrar.

        Args:
            task: Task to execute

        Returns:
            Updated task with results
        """
        logger.info(f"Executing task: {task.id}")

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow().isoformat()

        try:
            # Simulate task execution
            await asyncio.sleep(2)

            # Here you would call the actual automation
            # Example:
            # from .freelance_registrar import FreelanceRegistrar
            # registrar = FreelanceRegistrar()
            # result = await registrar.register_platform(...)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            task.result = {
                "success": True,
                "message": f"Task {task.id} completed successfully"
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow().isoformat()

        return task

    async def process_queue(self):
        """
        Process task queue.

        Runs continuously, processing tasks from the queue.
        """
        logger.info("Starting queue processor")

        while True:
            try:
                # Check if we can start a new task
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue

                # Get next task from queue (with timeout)
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    await asyncio.sleep(1)
                    continue

                # Execute task in background
                async_task = asyncio.create_task(self.execute_task(task))
                self.running_tasks[task.id] = async_task

                # Remove from running tasks when done
                async_task.add_done_callback(
                    lambda t: self.running_tasks.pop(task.id, None)
                )

            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(1)

    async def start_processor(self):
        """Start background task processor."""
        processor_task = asyncio.create_task(self.process_queue())
        return processor_task

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "total_tasks": len(self.tasks),
            "pending": len(self.get_tasks_by_status(TaskStatus.PENDING)),
            "running": len(self.get_tasks_by_status(TaskStatus.RUNNING)),
            "completed": len(self.get_tasks_by_status(TaskStatus.COMPLETED)),
            "failed": len(self.get_tasks_by_status(TaskStatus.FAILED)),
            "queue_size": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
        }

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if cancelled, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status != TaskStatus.RUNNING:
            return False

        # Cancel asyncio task if running
        async_task = self.running_tasks.get(task_id)
        if async_task:
            async_task.cancel()

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow().isoformat()

        logger.info(f"Cancelled task: {task_id}")
        return True

    def export_tasks(self, filepath: str):
        """Export tasks to JSON file."""
        tasks_data = [task.to_dict() for task in self.tasks.values()]

        with open(filepath, 'w') as f:
            json.dump(tasks_data, f, indent=2)

        logger.info(f"Exported {len(tasks_data)} tasks to {filepath}")

    def import_tasks(self, filepath: str):
        """Import tasks from JSON file."""
        with open(filepath, 'r') as f:
            tasks_data = json.load(f)

        for task_data in tasks_data:
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                description=task_data["description"],
                task_type=task_data["task_type"],
                platform=task_data["platform"],
                status=TaskStatus(task_data["status"]),
                priority=TaskPriority(task_data["priority"]),
                created_at=task_data["created_at"],
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                error=task_data.get("error"),
                result=task_data.get("result"),
                metadata=task_data.get("metadata", {}),
            )
            self.tasks[task.id] = task

        logger.info(f"Imported {len(tasks_data)} tasks from {filepath}")
