"""
Role-Based Access Control (RBAC) middleware.

Provides decorators for role and permission-based access control.
"""

import logging
from typing import List
from functools import wraps

from quart import request, jsonify

logger = logging.getLogger(__name__)


class RBACMiddleware:
    """
    Role-Based Access Control handler.
    
    Defines roles and their permissions, and provides decorators
    for enforcing access control on endpoints.
    
    Attributes:
        roles: Dict mapping role names to list of permissions
    """

    def __init__(self):
        """Initialize RBAC with default roles."""
        self.roles = {
            "admin": [
                "read",
                "write",
                "delete",
                "audit",
                "manage_users",
                "manage_roles",
            ],
            "manager": [
                "read",
                "write",
                "delete",
                "audit",
                "manage_agents",
            ],
            "user": ["read", "write", "manage_own_agents"],
            "viewer": ["read"],
            "guest": [],
        }

    def has_role(self, required_roles: List[str]):
        """
        Decorator: Require user to have one of specified roles.
        
        Args:
            required_roles: List of roles that satisfy requirement
            
        Returns:
            Decorator function
            
        Example:
            @app.route('/admin')
            @rbac.has_role(['admin'])
            async def admin_endpoint():
                return {'message': 'Admin only'}, 200
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                try:
                    # Get user from request context
                    user = getattr(request, "auth_user", None)
                    
                    if not user:
                        logger.warning("Request missing auth_user context")
                        return jsonify({"error": "Unauthorized"}), 401
                    
                    user_roles = user.get("roles", [])
                    
                    # Check if user has any of the required roles
                    if not any(role in required_roles for role in user_roles):
                        logger.warning(
                            f"User {user.get('sub')} denied access. "
                            f"Has {user_roles}, requires {required_roles}"
                        )
                        return jsonify(
                            {
                                "error": "Insufficient permissions",
                                "required_roles": required_roles,
                                "user_roles": user_roles,
                            }
                        ), 403
                    
                    # Call original function
                    return await f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error in role check: {e}")
                    return jsonify({"error": "Authorization error"}), 500
            
            return decorated_function
        return decorator

    def has_permission(self, required_permission: str):
        """
        Decorator: Require user to have specific permission.
        
        Checks all user roles and verifies if any role grants
        the required permission.
        
        Args:
            required_permission: Permission name to require
            
        Returns:
            Decorator function
            
        Example:
            @app.route('/delete')
            @rbac.has_permission('delete')
            async def delete_endpoint():
                return {'message': 'Deleted'}, 200
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                try:
                    # Get user from request context
                    user = getattr(request, "auth_user", None)
                    
                    if not user:
                        logger.warning("Request missing auth_user context")
                        return jsonify({"error": "Unauthorized"}), 401
                    
                    user_roles = user.get("roles", [])
                    
                    # Check if any user role has the required permission
                    has_permission = False
                    for role in user_roles:
                        if required_permission in self.roles.get(role, []):
                            has_permission = True
                            break
                    
                    if not has_permission:
                        logger.warning(
                            f"User {user.get('sub')} denied permission "
                            f"'{required_permission}'. Has roles {user_roles}"
                        )
                        return jsonify(
                            {
                                "error": "Permission denied",
                                "required_permission": required_permission,
                            }
                        ), 403
                    
                    # Call original function
                    return await f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error in permission check: {e}")
                    return jsonify({"error": "Authorization error"}), 500
            
            return decorated_function
        return decorator

    def has_all_permissions(self, required_permissions: List[str]):
        """
        Decorator: Require user to have ALL specified permissions.
        
        Args:
            required_permissions: List of permissions required
            
        Returns:
            Decorator function
        """
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                try:
                    user = getattr(request, "auth_user", None)
                    
                    if not user:
                        return jsonify({"error": "Unauthorized"}), 401
                    
                    user_roles = user.get("roles", [])
                    
                    # Get all permissions for user
                    user_permissions = set()
                    for role in user_roles:
                        user_permissions.update(self.roles.get(role, []))
                    
                    # Check if user has all required permissions
                    if not all(p in user_permissions for p in required_permissions):
                        missing = set(required_permissions) - user_permissions
                        logger.warning(
                            f"User {user.get('sub')} missing permissions: {missing}"
                        )
                        return jsonify(
                            {
                                "error": "Insufficient permissions",
                                "missing_permissions": list(missing),
                            }
                        ), 403
                    
                    return await f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error in permission check: {e}")
                    return jsonify({"error": "Authorization error"}), 500
            
            return decorated_function
        return decorator

    def get_role_permissions(self, role: str) -> List[str]:
        """
        Get list of permissions for a role.
        
        Args:
            role: Role name
            
        Returns:
            List of permissions for role
        """
        return self.roles.get(role, [])

    def add_role(self, role: str, permissions: List[str]) -> None:
        """
        Add or update a role.
        
        Args:
            role: Role name
            permissions: List of permissions for role
        """
        self.roles[role] = permissions
        logger.info(f"Added/updated role '{role}' with permissions {permissions}")

    def get_all_roles(self) -> List[str]:
        """Get list of all available roles."""
        return list(self.roles.keys())
