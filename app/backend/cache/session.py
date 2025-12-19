"""
Session management using Redis.

Provides distributed session storage for multi-replica deployments.
Follows Microsoft Azure and GitHub Enterprise patterns.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from .cache import get_redis_manager

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager with Redis backend.
    
    Features:
    - Distributed session storage
    - Automatic expiry
    - JSON serialization
    - Fallback to in-memory
    """
    
    def __init__(self, session_ttl: int = 3600):
        """
        Initialize session manager.
        
        Args:
            session_ttl: Session TTL in seconds (default 1 hour)
        """
        self.session_ttl = session_ttl
        self.redis = get_redis_manager()
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"
    
    async def create_session(self, user_id: Optional[str] = None, data: Optional[Dict] = None) -> str:
        """
        Create new session.
        
        Args:
            user_id: User identifier
            data: Initial session data
            
        Returns:
            Session ID
        """
        session_id = str(uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "data": data or {}
        }
        
        key = self._session_key(session_id)
        await self.redis.set(key, session_data, expiry=self.session_ttl)
        
        logger.debug(f"Created session: {session_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dict or None
        """
        key = self._session_key(session_id)
        session_data = await self.redis.get(key)
        
        if session_data:
            # Update last activity and extend TTL
            session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
            await self.redis.set(key, session_data, expiry=self.session_ttl)
        
        return session_data
    
    async def update_session(self, session_id: str, data: Dict) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session identifier
            data: Data to merge into session
            
        Returns:
            True if successful
        """
        key = self._session_key(session_id)
        session_data = await self.redis.get(key)
        
        if not session_data:
            logger.warning(f"Session not found: {session_id}")
            return False
        
        # Merge data
        session_data["data"].update(data)
        session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        await self.redis.set(key, session_data, expiry=self.session_ttl)
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted
        """
        key = self._session_key(session_id)
        result = await self.redis.delete(key)
        
        if result:
            logger.debug(f"Deleted session: {session_id}")
        return result
    
    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        key = self._session_key(session_id)
        return await self.redis.exists(key)


# Global instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(session_ttl: int = 3600) -> SessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_ttl=session_ttl)
    return _session_manager
