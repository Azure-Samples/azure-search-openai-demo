"""
Automation API routes for freelance platform registration.

This blueprint provides REST API endpoints for managing automated
registration tasks on freelance platforms.
"""

import asyncio
import json
import logging
from typing import Any, Dict
from quart import Blueprint, jsonify, request, current_app
from decorators import authenticated

from automation.freelance_registrar import (
    FreelanceRegistrar,
    PlatformType,
    RegistrationData,
    APIConfig,
    RegistrationResult,
)
from automation.mcp_integration import MCPTaskManager, Task, TaskPriority, TaskStatus
from automation.browser_agent import BrowserConfig

logger = logging.getLogger(__name__)

automation_bp = Blueprint("automation", __name__)

# Global task manager instance
task_manager = MCPTaskManager()


@automation_bp.before_app_serving
async def startup():
    """Start task processor on app startup."""
    logger.info("Starting automation task processor")
    await task_manager.start_processor()


@automation_bp.route("/automation/platforms", methods=["GET"])
@authenticated
async def list_platforms(auth_claims: dict[str, Any]):
    """
    List supported freelance platforms.

    Returns:
        JSON list of supported platforms
    """
    platforms = [
        {
            "id": platform.value,
            "name": platform.name,
            "supported_features": ["registration", "api_setup", "webhooks"]
        }
        for platform in PlatformType
        if platform != PlatformType.CUSTOM
    ]

    return jsonify({"platforms": platforms})


@automation_bp.route("/automation/register", methods=["POST"])
@authenticated
async def register_platform(auth_claims: dict[str, Any]):
    """
    Register on a freelance platform.

    Request body:
    {
        "platform": "upwork",
        "registration_data": {
            "email": "user@example.com",
            "password": "password",
            "first_name": "John",
            "last_name": "Doe",
            "country": "US"
        },
        "api_config": {
            "webhook_url": "https://example.com/webhook"
        },
        "headless": true
    }

    Returns:
        Registration result with status and details
    """
    try:
        data = await request.get_json()

        # Parse platform
        platform_str = data.get("platform")
        try:
            platform = PlatformType(platform_str)
        except ValueError:
            return jsonify({"error": f"Unsupported platform: {platform_str}"}), 400

        # Parse registration data
        reg_data = data.get("registration_data", {})
        registration_data = RegistrationData(
            email=reg_data.get("email"),
            password=reg_data.get("password"),
            first_name=reg_data.get("first_name"),
            last_name=reg_data.get("last_name"),
            company_name=reg_data.get("company_name"),
            country=reg_data.get("country", "US"),
            phone=reg_data.get("phone"),
            skills=reg_data.get("skills", []),
            bio=reg_data.get("bio"),
            portfolio_url=reg_data.get("portfolio_url"),
        )

        # Parse API config
        api_data = data.get("api_config", {})
        api_config = APIConfig(
            webhook_url=api_data.get("webhook_url"),
            scopes=api_data.get("scopes", ["read", "write"]),
        )

        # Browser config
        browser_config = BrowserConfig(
            headless=data.get("headless", False),
            slow_mo=data.get("slow_mo", 100),
        )

        # Execute registration
        registrar = FreelanceRegistrar(browser_config)
        result = await registrar.register_platform(
            platform=platform,
            registration_data=registration_data,
            api_config=api_config,
            setup_api=data.get("setup_api", True),
            setup_webhooks=data.get("setup_webhooks", True),
        )

        return jsonify(result.to_dict())

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": str(e)}), 500


@automation_bp.route("/automation/tasks", methods=["POST"])
@authenticated
async def create_task(auth_claims: dict[str, Any]):
    """
    Create a new automation task.

    Request body:
    {
        "title": "Register on Upwork",
        "description": "Complete registration with API setup",
        "task_type": "registration",
        "platform": "upwork",
        "priority": "high",
        "metadata": {
            "email": "user@example.com"
        }
    }

    Returns:
        Created task details
    """
    try:
        data = await request.get_json()

        # Parse priority
        priority_str = data.get("priority", "medium")
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.MEDIUM

        # Create task
        task = task_manager.create_task(
            title=data.get("title"),
            description=data.get("description"),
            task_type=data.get("task_type"),
            platform=data.get("platform"),
            priority=priority,
            metadata=data.get("metadata"),
        )

        # Enqueue task
        await task_manager.enqueue_task(task)

        return jsonify(task.to_dict()), 201

    except Exception as e:
        logger.error(f"Task creation error: {e}")
        return jsonify({"error": str(e)}), 500


@automation_bp.route("/automation/tasks", methods=["GET"])
@authenticated
async def list_tasks(auth_claims: dict[str, Any]):
    """
    List all automation tasks.

    Query parameters:
    - status: Filter by status (pending, running, completed, failed)
    - platform: Filter by platform

    Returns:
        List of tasks
    """
    try:
        status_filter = request.args.get("status")
        platform_filter = request.args.get("platform")

        tasks = task_manager.get_all_tasks()

        # Apply filters
        if status_filter:
            try:
                status = TaskStatus(status_filter)
                tasks = [t for t in tasks if t.status == status]
            except ValueError:
                pass

        if platform_filter:
            tasks = [t for t in tasks if t.platform == platform_filter]

        tasks_data = [task.to_dict() for task in tasks]

        return jsonify({
            "tasks": tasks_data,
            "total": len(tasks_data)
        })

    except Exception as e:
        logger.error(f"Task listing error: {e}")
        return jsonify({"error": str(e)}), 500


@automation_bp.route("/automation/tasks/<task_id>", methods=["GET"])
@authenticated
async def get_task(task_id: str, auth_claims: dict[str, Any]):
    """
    Get task details by ID.

    Returns:
        Task details or 404 if not found
    """
    task = task_manager.get_task(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(task.to_dict())


@automation_bp.route("/automation/tasks/<task_id>/cancel", methods=["POST"])
@authenticated
async def cancel_task(task_id: str, auth_claims: dict[str, Any]):
    """
    Cancel a running task.

    Returns:
        Success status
    """
    success = await task_manager.cancel_task(task_id)

    if not success:
        return jsonify({"error": "Task not found or cannot be cancelled"}), 400

    return jsonify({"success": True, "message": f"Task {task_id} cancelled"})


@automation_bp.route("/automation/stats", methods=["GET"])
@authenticated
async def get_stats(auth_claims: dict[str, Any]):
    """
    Get automation statistics.

    Returns:
        Statistics about tasks and queue
    """
    stats = task_manager.get_queue_stats()

    return jsonify(stats)


@automation_bp.route("/automation/batch-register", methods=["POST"])
@authenticated
async def batch_register(auth_claims: dict[str, Any]):
    """
    Register on multiple platforms in one request.

    Request body:
    {
        "platforms": ["upwork", "fiverr", "freelancer"],
        "registration_data": {
            "email": "user@example.com",
            ...
        },
        "api_config": {...}
    }

    Returns:
        List of registration results
    """
    try:
        data = await request.get_json()

        # Parse platforms
        platform_strs = data.get("platforms", [])
        platforms = []
        for p in platform_strs:
            try:
                platforms.append(PlatformType(p))
            except ValueError:
                logger.warning(f"Skipping unsupported platform: {p}")

        if not platforms:
            return jsonify({"error": "No valid platforms specified"}), 400

        # Parse registration data
        reg_data = data.get("registration_data", {})
        registration_data = RegistrationData(
            email=reg_data.get("email"),
            password=reg_data.get("password"),
            first_name=reg_data.get("first_name"),
            last_name=reg_data.get("last_name"),
            country=reg_data.get("country", "US"),
        )

        # Parse API config
        api_data = data.get("api_config", {})
        api_config = APIConfig(
            webhook_url=api_data.get("webhook_url"),
        )

        # Browser config
        browser_config = BrowserConfig(
            headless=data.get("headless", False),
        )

        # Execute batch registration
        registrar = FreelanceRegistrar(browser_config)
        results = await registrar.register_multiple_platforms(
            platforms=platforms,
            registration_data=registration_data,
            api_config=api_config,
        )

        return jsonify({
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
        })

    except Exception as e:
        logger.error(f"Batch registration error: {e}")
        return jsonify({"error": str(e)}), 500


@automation_bp.route("/automation/health", methods=["GET"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return jsonify({
        "status": "healthy",
        "task_processor": "running",
        "stats": task_manager.get_queue_stats()
    })
