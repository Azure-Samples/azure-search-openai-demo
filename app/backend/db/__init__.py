"""
Database module for Agent Management System.

Provides PostgreSQL persistence with async support via SQLAlchemy.
Follows Microsoft Azure best practices for database connectivity.
"""

from .database import (
    DatabaseManager,
    get_db_session,
    init_database,
    close_database,
)
from .models import (
    Base,
    BrowserAgentModel,
    TaskModel,
    AuditLogModel,
    ProjectModel,
)

__all__ = [
    "DatabaseManager",
    "get_db_session",
    "init_database",
    "close_database",
    "Base",
    "BrowserAgentModel",
    "TaskModel",
    "AuditLogModel",
    "ProjectModel",
]
