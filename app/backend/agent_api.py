"""
Agent Management API Blueprint.

Provides REST API endpoints for managing browser agents and Taskade integration.
Uses official Taskade REST API (no local MCP server - memory efficient).

ENTERPRISE FEATURES:
- PostgreSQL persistence with fallback to in-memory
- Audit logging for compliance
- Health checks for monitoring
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
from quart import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(str(Path(__file__).parent / "automation"))

from automation.browser_agent import BrowserAgent, BrowserConfig
from automation.mcp_integration import MCPTaskManager, TaskPriority

# Database imports (with graceful fallback)
try:
    from db import get_db_session, get_db_manager
    from db.models import BrowserAgentModel, TaskModel, AuditLogModel, AgentStatus, TaskStatus
    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database module not available. Running in memory-only mode.")
    DB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint("agent_api", __name__, url_prefix="/api/agents")

# Taskade API Configuration
TASKADE_API_KEY = os.getenv("TASKADE_API_KEY", "tskdp_WE8Y2qtsVeQgjVNzxQBBNC4ssbeEs8h8xM")
TASKADE_API_BASE = "https://api.taskade.com/v1"
TASKADE_HEADERS = {
    "Authorization": f"Bearer {TASKADE_API_KEY}",
    "Content-Type": "application/json"
}


class TaskadeDirectAPI:
    """Direct Taskade REST API client (no MCP server overhead)."""

    @staticmethod
    async def get_workspaces() -> dict:
        """Get all workspaces."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{TASKADE_API_BASE}/workspaces",
                    headers=TASKADE_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"Taskade API error: {e}")
            return {"error": str(e)}

    @staticmethod
    async def list_projects(workspace_id: str | None = None) -> dict:
        """List projects."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{TASKADE_API_BASE}/projects"
                if workspace_id:
                    url += f"?workspace_id={workspace_id}"

                async with session.get(url, headers=TASKADE_HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"List projects error: {e}")
            return {"error": str(e)}

    @staticmethod
    async def create_project(title: str, description: str | None = None) -> dict:
        """Create project."""
        try:
            payload = {"title": title}
            if description:
                payload["description"] = description

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{TASKADE_API_BASE}/projects",
                    headers=TASKADE_HEADERS,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in (200, 201):
                        return await resp.json()
                    else:
                        return {"error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"Create project error: {e}")
            return {"error": str(e)}

    @staticmethod
    async def list_tasks(project_id: str) -> dict:
        """List tasks in project."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{TASKADE_API_BASE}/projects/{project_id}/tasks",
                    headers=TASKADE_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"List tasks error: {e}")
            return {"error": str(e)}

    @staticmethod
    async def create_task(
        project_id: str,
        title: str,
        description: str | None = None,
        priority: str | None = None
    ) -> dict:
        """Create task."""
        try:
            payload = {"title": title}
            if description:
                payload["description"] = description
            if priority:
                payload["priority"] = priority

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{TASKADE_API_BASE}/projects/{project_id}/tasks",
                    headers=TASKADE_HEADERS,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in (200, 201):
                        return await resp.json()
                    else:
                        return {"error": f"Status {resp.status}"}
        except Exception as e:
            logger.error(f"Create task error: {e}")
            return {"error": str(e)}


# Browser agent manager
_browser_agents: dict[str, BrowserAgent] = {}


async def _get_or_create_agent(agent_id: str, headless: bool = False, channel: str = "msedge") -> BrowserAgent:
    """Create browser agent if not exists."""
    if agent_id not in _browser_agents:
        config = BrowserConfig(headless=headless)
        agent = BrowserAgent(config)
        await agent.start(channel=channel)
        _browser_agents[agent_id] = agent
    return _browser_agents[agent_id]


# REST API Routes

@bp.route("/browser", methods=["GET"])
async def list_agents():
    """List all active browser agents."""
    agents = []
    for agent_id, agent in _browser_agents.items():
        agents.append({
            "id": agent_id,
            "status": "active" if agent.browser else "stopped",
            "channel": "msedge"
        })

    return jsonify({
        "agents": agents,
        "count": len(agents)
    })


@bp.route("/browser", methods=["POST"])
async def create_agent():
    """Create new browser agent with database persistence."""
    try:
        data = await request.get_json() or {}
        agent_id = data.get("agent_id", f"agent_{datetime.now(timezone.utc).timestamp()}")
        config = data.get("config", {})
        headless = config.get("headless", False)
        channel = config.get("channel", "msedge")

        # Create browser agent
        agent = await _get_or_create_agent(agent_id, headless=headless, channel=channel)

        # Save to database (with fallback)
        if DB_AVAILABLE:
            async with get_db_session() as session:
                if session:
                    from db.helpers import save_agent_to_db, log_audit_event
                    await save_agent_to_db(
                        session, agent_id, channel, headless, config
                    )
                    await log_audit_event(
                        session,
                        event_type="agent.create",
                        action="CREATE",
                        resource_type="agent",
                        resource_id=agent_id,
                        details={"channel": channel, "headless": headless},
                        success=True
                    )

        logger.info(f"Created agent: {agent_id}")
        return jsonify({
            "success": True,
            "agent_id": agent_id,
            "status": "running",
            "persisted": DB_AVAILABLE
        }), 201

    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        
        # Log failure audit event
        if DB_AVAILABLE:
            async with get_db_session() as session:
                if session:
                    from db.helpers import log_audit_event
                    await log_audit_event(
                        session,
                        event_type="agent.create",
                        action="CREATE",
                        resource_type="agent",
                        success=False,
                        error_message=str(e)
                    )
        
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/browser/<agent_id>", methods=["GET"])
async def get_agent(agent_id: str):
    """Get agent status."""
    agent = _browser_agents.get(agent_id)

    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    return jsonify({
        "agent_id": agent_id,
        "status": "active" if agent.browser else "stopped"
    })


@bp.route("/browser/<agent_id>", methods=["DELETE"])
async def delete_agent(agent_id: str):
    """Stop and delete agent with database persistence."""
    try:
        agent = _browser_agents.get(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404

        # Stop browser agent
        await agent.stop()
        del _browser_agents[agent_id]

        # Delete from database (soft delete)
        if DB_AVAILABLE:
            async with get_db_session() as session:
                if session:
                    from db.helpers import delete_agent_from_db, log_audit_event
                    await delete_agent_from_db(session, agent_id, soft_delete=True)
                    await log_audit_event(
                        session,
                        event_type="agent.delete",
                        action="DELETE",
                        resource_type="agent",
                        resource_id=agent_id,
                        success=True
                    )

        logger.info(f"Deleted agent: {agent_id}")
        return jsonify({"success": True, "agent_id": agent_id})

    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/taskade", methods=["GET"])
async def get_taskade_info():
    """Get Taskade workspace info."""
    result = await TaskadeDirectAPI.get_workspaces()
    success = "error" not in result

    return jsonify({
        "success": success,
        "workspaces": result if success else [],
        "error": result.get("error") if not success else None
    })


@bp.route("/taskade/projects", methods=["GET"])
async def list_taskade_projects():
    """List Taskade projects."""
    result = await TaskadeDirectAPI.list_projects()
    success = "error" not in result

    return jsonify({
        "success": success,
        "projects": result.get("items", []) if success and "items" in result else (result if success else []),
        "error": result.get("error") if not success else None
    })


@bp.route("/taskade/projects", methods=["POST"])
async def create_taskade_project():
    """Create Taskade project."""
    try:
        data = await request.get_json() or {}

        if not data.get("title"):
            return jsonify({"error": "title is required"}), 400

        result = await TaskadeDirectAPI.create_project(
            title=data["title"],
            description=data.get("description")
        )

        success = "error" not in result
        status = 201 if success else 500

        return jsonify({
            "success": success,
            "project": result if success else None,
            "error": result.get("error") if not success else None
        }), status

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/taskade/projects/<project_id>/tasks", methods=["GET"])
async def list_taskade_tasks(project_id: str):
    """List tasks in Taskade project."""
    result = await TaskadeDirectAPI.list_tasks(project_id)
    success = "error" not in result

    return jsonify({
        "success": success,
        "project_id": project_id,
        "tasks": result.get("items", []) if success and "items" in result else (result if success else []),
        "error": result.get("error") if not success else None
    })


@bp.route("/taskade/projects/<project_id>/tasks", methods=["POST"])
async def create_taskade_task(project_id: str):
    """Create task in Taskade project."""
    try:
        data = await request.get_json() or {}

        if not data.get("title"):
            return jsonify({"error": "title is required"}), 400

        result = await TaskadeDirectAPI.create_task(
            project_id=project_id,
            title=data["title"],
            description=data.get("description"),
            priority=data.get("priority")
        )

        success = "error" not in result
        status = 201 if success else 500

        return jsonify({
            "success": success,
            "task": result if success else None,
            "error": result.get("error") if not success else None
        }), status

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/mcp/tasks", methods=["GET"])
async def list_mcp_tasks():
    """List MCP task queue."""
    task_manager = MCPTaskManager()
    tasks = task_manager.list_tasks()

    return jsonify({
        "success": True,
        "tasks": [t.to_dict() for t in tasks]
    })


@bp.route("/mcp/tasks", methods=["POST"])
async def create_mcp_task():
    """Create MCP task."""
    try:
        data = await request.get_json() or {}

        task_manager = MCPTaskManager()
        task = await task_manager.create_task(
            title=data.get("title", ""),
            description=data.get("description", ""),
            task_type=data.get("task_type", "generic"),
            platform=data.get("platform", "unknown"),
            priority=TaskPriority(data.get("priority", "medium"))
        )

        return jsonify({
            "success": True,
            "task": task.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Failed to create MCP task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/health", methods=["GET"])
async def health_check():
    """
    API health check - basic liveness probe.
    
    Returns simple OK status for Kubernetes/load balancer probes.
    """
    return jsonify({
        "status": "healthy",
        "service": "agent-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@bp.route("/health/ready", methods=["GET"])
async def readiness_check():
    """
    Readiness check with detailed component status.
    
    Checks:
    - Database connectivity (if configured)
    - Taskade API availability
    - In-memory state
    
    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "service": "agent-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    is_ready = True
    
    # Check database
    if DB_AVAILABLE:
        try:
            db_manager = get_db_manager()
            db_health = await db_manager.health_check()
            checks["components"]["database"] = db_health
            if db_health["status"] not in ("healthy", "degraded"):
                is_ready = False
        except Exception as e:
            checks["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            is_ready = False
    else:
        checks["components"]["database"] = {
            "status": "not_configured",
            "mode": "fallback"
        }
    
    # Check Taskade API (simple connectivity test)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TASKADE_API_BASE}/user",
                headers=TASKADE_HEADERS,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    checks["components"]["taskade_api"] = {
                        "status": "healthy"
                    }
                else:
                    checks["components"]["taskade_api"] = {
                        "status": "degraded",
                        "http_status": resp.status
                    }
    except Exception as e:
        checks["components"]["taskade_api"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        is_ready = False
    
    # Check Redis cache
    try:
        from cache import get_redis_manager
        redis_manager = get_redis_manager()
        if not redis_manager._is_initialized:
            await redis_manager.initialize()
        redis_health = await redis_manager.health_check()
        checks["components"]["redis"] = redis_health
        # Redis degradation is OK (fallback mode)
    except Exception as e:
        checks["components"]["redis"] = {
            "status": "not_available",
            "error": str(e)
        }
    
    # Check in-memory state
    checks["components"]["memory_state"] = {
        "status": "healthy",
        "active_agents": len(_browser_agents)
    }
    
    # Overall status
    checks["status"] = "ready" if is_ready else "not_ready"
    status_code = 200 if is_ready else 503
    
    return jsonify(checks), status_code


@bp.route("/health/live", methods=["GET"])
async def liveness_check():
    """
    Liveness check - basic process health.
    
    Always returns 200 if process is responding.
    For Kubernetes liveness probes.
    """
    return jsonify({
        "status": "alive",
        "service": "agent-api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
