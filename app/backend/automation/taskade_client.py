"""Taskade Enterprise API Client"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

class TaskadeAPIError(Exception):
    pass

@dataclass
class TaskadeConfig:
    api_key: str
    base_url: str = "https://www.taskade.com/api/v1"
    timeout: int = 30

@dataclass
class Workspace:
    id: str
    name: str

@dataclass
class Project:
    id: str
    name: str
    workspace_id: str

@dataclass
class Task:
    id: str
    content: str
    project_id: str
    completed: bool = False

class TaskadeClient:
    def __init__(self, config: TaskadeConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        url = f"{self.config.base_url}{endpoint}"
        async with self.session.request(method, url, **kwargs) as resp:
            if resp.status != 200:
                raise TaskadeAPIError(f"API error: {resp.status}")
            return await resp.json()

    async def get_workspaces(self) -> List[Workspace]:
        data = await self._request("GET", "/workspaces")
        return [Workspace(id=w["id"], name=w["name"]) for w in data.get("items", [])]

    async def create_workspace(self, name: str) -> Workspace:
        data = await self._request("POST", "/workspaces", json={"name": name})
        return Workspace(id=data["id"], name=data["name"])

    async def create_project(self, workspace_id: str, name: str) -> Project:
        data = await self._request("POST", f"/workspaces/{workspace_id}/projects", json={"name": name})
        return Project(id=data["id"], name=data["name"], workspace_id=workspace_id)

    async def create_task(self, project_id: str, content: str) -> Task:
        data = await self._request("POST", f"/projects/{project_id}/tasks", json={"content": content})
        return Task(id=data["id"], content=content, project_id=project_id)

    async def update_task(self, task_id: str, completed: bool = None) -> Task:
        data = await self._request("PATCH", f"/tasks/{task_id}", json={"completed": completed})
        return Task(id=data["id"], content="", project_id="", completed=data.get("completed", False))

@dataclass
class TaskadeFreelanceIntegration:
    client: TaskadeClient
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None

    async def setup_workspace(self, name: str = "Freelance Automation") -> str:
        workspaces = await self.client.get_workspaces()
        for ws in workspaces:
            if ws.name == name:
                self.workspace_id = ws.id
                return ws.id
        ws = await self.client.create_workspace(name)
        self.workspace_id = ws.id
        return ws.id

    async def create_registration_project(self, platform: str) -> str:
        if not self.workspace_id:
            await self.setup_workspace()
        project = await self.client.create_project(self.workspace_id, f"Registration: {platform}")
        self.project_id = project.id
        return project.id

    async def track_progress(self, steps: List[str]) -> List[str]:
        task_ids = []
        for step in steps:
            task = await self.client.create_task(self.project_id, step)
            task_ids.append(task.id)
        return task_ids
