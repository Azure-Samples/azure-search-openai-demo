"""
Agent Management API Blueprint.

Provides REST API endpoints for managing browser agents and Taskade integration.
Uses official Taskade REST API (no local MCP server - memory efficient).
"""

import asyncio
import logging
import os
import aiohttp
import sys
from datetime import datetime
from pathlib import Path

from quart import Blueprint, jsonify, request

sys.path.append(str(Path(__file__).parent / "automation"))

from automation.browser_agent import BrowserAgent, BrowserConfig
from automation.mcp_integration import MCPTaskManager, TaskPriority

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
    """Create new browser agent."""
    try:
        data = await request.get_json() or {}
        agent_id = data.get("agent_id", f"agent_{datetime.now().timestamp()}")
        config = data.get("config", {})
        
        agent = await _get_or_create_agent(
            agent_id,
            headless=config.get("headless", False),
            channel=config.get("channel", "msedge")
        )
        
        logger.info(f"Created agent: {agent_id}")
        return jsonify({
            "success": True,
            "agent_id": agent_id,
            "status": "running"
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
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
    """Stop and delete agent."""
    try:
        agent = _browser_agents.get(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found"}), 404
        
        await agent.stop()
        del _browser_agents[agent_id]
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
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "agent_api",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_running": len(_browser_agents),
        "taskade_api": TASKADE_API_BASE
    })
