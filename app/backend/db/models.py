"""
SQLAlchemy models for Agent Management System.

Models follow Microsoft Azure and GitHub Enterprise best practices:
- Timestamps for audit trail
- Soft deletes where applicable
- JSON fields for flexible metadata
- Indexes on frequently queried columns
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class TaskStatus(enum.Enum):
    """Task status enum matching MCP integration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(enum.Enum):
    """Task priority enum matching MCP integration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AgentStatus(enum.Enum):
    """Browser agent status."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class BrowserAgentModel(Base):
    """
    Browser Agent persistence model.
    
    Stores browser automation agent state for persistence across restarts.
    Follows Azure best practices: timestamps, soft delete, metadata.
    """
    __tablename__ = "browser_agents"
    
    # Primary key
    id = Column(String(255), primary_key=True, index=True)
    
    # Agent configuration
    channel = Column(String(50), nullable=False, default="msedge")  # msedge, chrome, chromium
    headless = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.CREATED)
    
    # Configuration as JSON (flexible)
    config = Column(JSON, nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=True)  # User ID from auth
    user_agent = Column(String(512), nullable=True)
    viewport_width = Column(Integer, default=1920)
    viewport_height = Column(Integer, default=1080)
    
    # Audit fields
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Statistics
    total_actions = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    last_action_at = Column(DateTime, nullable=True)
    
    # Relationships
    tasks = relationship("TaskModel", back_populates="agent", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_browser_agents_status", "status"),
        Index("ix_browser_agents_created_by", "created_by"),
        Index("ix_browser_agents_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<BrowserAgent(id='{self.id}', status='{self.status.value}', channel='{self.channel}')>"


class ProjectModel(Base):
    """
    Taskade Project model.
    
    Stores project metadata for tracking automation projects.
    """
    __tablename__ = "projects"
    
    # Primary key
    id = Column(String(255), primary_key=True, index=True)
    
    # Project info
    name = Column(String(512), nullable=False)
    workspace_id = Column(String(255), nullable=True)
    folder_id = Column(String(255), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Audit fields
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    tasks = relationship("TaskModel", back_populates="project", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_projects_workspace_id", "workspace_id"),
        Index("ix_projects_created_by", "created_by"),
    )
    
    def __repr__(self):
        return f"<Project(id='{self.id}', name='{self.name}')>"


class TaskModel(Base):
    """
    Task model for MCP and Taskade integration.
    
    Stores task state for persistence and audit trail.
    """
    __tablename__ = "tasks"
    
    # Primary key
    id = Column(String(255), primary_key=True, index=True)
    
    # Task info
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    
    # Foreign keys
    project_id = Column(String(255), ForeignKey("projects.id"), nullable=True)
    agent_id = Column(String(255), ForeignKey("browser_agents.id"), nullable=True)
    
    # Task details
    task_type = Column(String(100), nullable=True)  # e.g., "browser_automation", "api_call"
    payload = Column(JSON, nullable=True)  # Task-specific data
    result = Column(JSON, nullable=True)  # Task result/output
    error_message = Column(Text, nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Audit fields
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = relationship("ProjectModel", back_populates="tasks")
    agent = relationship("BrowserAgentModel", back_populates="tasks")
    
    # Indexes
    __table_args__ = (
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_agent_id", "agent_id"),
        Index("ix_tasks_created_by", "created_by"),
        Index("ix_tasks_created_at", "created_at"),
    )
    
    def __repr__(self):
        return f"<Task(id='{self.id}', title='{self.title}', status='{self.status.value}')>"


class AuditLogModel(Base):
    """
    Audit log for compliance and security.
    
    Follows enterprise best practices:
    - Immutable (no updates/deletes)
    - Records all significant actions
    - Includes user context and IP
    """
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)  # e.g., "agent.create", "task.complete"
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, EXECUTE
    resource_type = Column(String(100), nullable=False)  # agent, task, project
    resource_id = Column(String(255), nullable=True, index=True)
    
    # User context
    user_id = Column(String(255), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(512), nullable=True)
    
    # Event data
    details = Column(JSON, nullable=True)  # Event-specific metadata
    old_value = Column(JSON, nullable=True)  # For UPDATE actions
    new_value = Column(JSON, nullable=True)  # For CREATE/UPDATE actions
    
    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamp (immutable)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_event_type", "event_type", "timestamp"),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event='{self.event_type}', user='{self.user_id}', time='{self.timestamp}')>"
