"""
Database helper functions for agent_api.

Provides persistence layer with automatic fallback to in-memory.
All functions are designed to work whether database is available or not.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    BrowserAgentModel,
    TaskModel,
    AuditLogModel,
    ProjectModel,
    AgentStatus,
    TaskStatus,
    TaskPriority,
)

logger = logging.getLogger(__name__)


async def save_agent_to_db(
    session: Optional[AsyncSession],
    agent_id: str,
    channel: str,
    headless: bool,
    config: Dict,
    created_by: Optional[str] = None
) -> bool:
    """
    Save browser agent to database.
    
    Args:
        session: Database session (None if DB not available)
        agent_id: Agent identifier
        channel: Browser channel (msedge, chrome, etc.)
        headless: Headless mode flag
        config: Agent configuration dict
        created_by: User ID who created the agent
        
    Returns:
        True if saved, False if fallback mode
    """
    if session is None:
        return False
    
    try:
        agent = BrowserAgentModel(
            id=agent_id,
            channel=channel,
            headless=headless,
            config=config,
            status=AgentStatus.RUNNING,
            created_by=created_by,
        )
        session.add(agent)
        await session.flush()
        logger.debug(f"Saved agent {agent_id} to database")
        return True
    except Exception as e:
        logger.error(f"Failed to save agent to DB: {e}")
        return False


async def update_agent_status(
    session: Optional[AsyncSession],
    agent_id: str,
    status: AgentStatus
) -> bool:
    """Update agent status in database."""
    if session is None:
        return False
    
    try:
        result = await session.execute(
            select(BrowserAgentModel).where(BrowserAgentModel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            agent.status = status
            agent.updated_at = datetime.now(timezone.utc)
            await session.flush()
            logger.debug(f"Updated agent {agent_id} status to {status.value}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to update agent status: {e}")
        return False


async def delete_agent_from_db(
    session: Optional[AsyncSession],
    agent_id: str,
    soft_delete: bool = True
) -> bool:
    """
    Delete agent from database.
    
    Args:
        session: Database session
        agent_id: Agent to delete
        soft_delete: If True, mark as deleted; if False, hard delete
    """
    if session is None:
        return False
    
    try:
        result = await session.execute(
            select(BrowserAgentModel).where(BrowserAgentModel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            if soft_delete:
                agent.deleted_at = datetime.now(timezone.utc)
                agent.status = AgentStatus.STOPPED
            else:
                await session.delete(agent)
            await session.flush()
            logger.debug(f"Deleted agent {agent_id} from database")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        return False


async def get_agent_from_db(
    session: Optional[AsyncSession],
    agent_id: str
) -> Optional[BrowserAgentModel]:
    """Retrieve agent from database."""
    if session is None:
        return None
    
    try:
        result = await session.execute(
            select(BrowserAgentModel).where(
                BrowserAgentModel.id == agent_id,
                BrowserAgentModel.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get agent from DB: {e}")
        return None


async def list_agents_from_db(
    session: Optional[AsyncSession],
    created_by: Optional[str] = None
) -> List[BrowserAgentModel]:
    """List all agents from database."""
    if session is None:
        return []
    
    try:
        query = select(BrowserAgentModel).where(
            BrowserAgentModel.deleted_at.is_(None)
        )
        if created_by:
            query = query.where(BrowserAgentModel.created_by == created_by)
        
        result = await session.execute(query.order_by(BrowserAgentModel.created_at.desc()))
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Failed to list agents from DB: {e}")
        return []


async def save_task_to_db(
    session: Optional[AsyncSession],
    task_id: str,
    title: str,
    description: Optional[str] = None,
    status: TaskStatus = TaskStatus.PENDING,
    priority: TaskPriority = TaskPriority.MEDIUM,
    project_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    task_type: Optional[str] = None,
    payload: Optional[Dict] = None,
    created_by: Optional[str] = None
) -> bool:
    """Save task to database."""
    if session is None:
        return False
    
    try:
        task = TaskModel(
            id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            agent_id=agent_id,
            task_type=task_type,
            payload=payload,
            created_by=created_by,
        )
        session.add(task)
        await session.flush()
        logger.debug(f"Saved task {task_id} to database")
        return True
    except Exception as e:
        logger.error(f"Failed to save task to DB: {e}")
        return False


async def log_audit_event(
    session: Optional[AsyncSession],
    event_type: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> bool:
    """
    Log audit event for compliance.
    
    Example event_types:
    - agent.create, agent.delete, agent.start, agent.stop
    - task.create, task.complete, task.fail
    - project.create, project.update
    """
    if session is None:
        # Still log to application logger even if DB unavailable
        logger.info(f"AUDIT: {event_type} - {action} on {resource_type}:{resource_id} by {user_id}")
        return False
    
    try:
        audit_log = AuditLogModel(
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=success,
            error_message=error_message,
        )
        session.add(audit_log)
        await session.flush()
        return True
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return False
