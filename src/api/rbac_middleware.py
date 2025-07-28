"""
Enhanced RBAC (Role-Based Access Control) Middleware for Kairos
Provides comprehensive multi-user authentication and authorization
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import asyncpg
from database.models.user import User, UserRole, ProjectRole, UserStatus
from database.models.audit import AuditLogger


class Permission:
    """Permission constants for fine-grained access control"""
    
    # System-wide permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    
    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    PROJECT_ADMIN = "project:admin"
    
    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    
    # MCP permissions
    MCP_READ = "mcp:read"
    MCP_WRITE = "mcp:write"
    MCP_EXECUTE = "mcp:execute"
    
    # Agent permissions
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_EXECUTE = "agent:execute"
    
    # API Key permissions
    API_KEY_CREATE = "api_key:create"
    API_KEY_READ = "api_key:read"
    API_KEY_DELETE = "api_key:delete"


class RolePermissionMatrix:
    """Maps roles to their allowed permissions"""
    
    PERMISSIONS = {
        # System-wide roles
        UserRole.SUPER_ADMIN.value: [
            Permission.SYSTEM_ADMIN,
            Permission.SYSTEM_READ,
            Permission.SYSTEM_WRITE,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_ADMIN,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_DELETE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_WRITE,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.AGENT_EXECUTE,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_READ,
            Permission.API_KEY_DELETE
        ],
        
        UserRole.ADMIN.value: [
            Permission.SYSTEM_READ,
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_ADMIN,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_WRITE,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.AGENT_EXECUTE,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_READ,
            Permission.API_KEY_DELETE
        ],
        
        UserRole.USER.value: [
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_WRITE,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_EXECUTE,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_READ
        ],
        
        UserRole.VIEWER.value: [
            Permission.PROJECT_READ,
            Permission.TASK_READ,
            Permission.MCP_READ,
            Permission.AGENT_READ
        ],
        
        # Project-specific roles
        ProjectRole.OWNER.value: [
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_ADMIN,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_DELETE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_WRITE,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.AGENT_EXECUTE
        ],
        
        ProjectRole.ADMIN.value: [
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_WRITE,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_WRITE,
            Permission.AGENT_EXECUTE
        ],
        
        ProjectRole.MEMBER.value: [
            Permission.PROJECT_READ,
            Permission.TASK_CREATE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_EXECUTE,
            Permission.MCP_READ,
            Permission.MCP_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_EXECUTE
        ],
        
        ProjectRole.VIEWER.value: [
            Permission.PROJECT_READ,
            Permission.TASK_READ,
            Permission.MCP_READ,
            Permission.AGENT_READ
        ]
    }
    
    @classmethod
    def get_permissions(cls, role: str) -> List[str]:
        """Get all permissions for a given role"""
        return cls.PERMISSIONS.get(role, [])
    
    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """Check if role has specific permission"""
        return permission in cls.get_permissions(role)


class RBACManager:
    """Manages Role-Based Access Control operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.user_model = User(db_pool)
        self.audit_logger = AuditLogger(db_pool)
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = await self.user_model.authenticate_user(email, password)
        if user:
            await self.audit_logger.log_auth_event(
                user_id=user['id'],
                action="login_success",
                details={"email": email}
            )
        else:
            await self.audit_logger.log_auth_event(
                action="login_failed",
                details={"email": email}
            )
        return user
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user info"""
        return await self.user_model.validate_api_key(api_key)
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission"""
        try:
            user = await self.user_model.get_user(user_id)
            if not user or user['status'] != UserStatus.ACTIVE.value:
                return False
            
            # Check system-wide permissions first
            system_permissions = RolePermissionMatrix.get_permissions(user['role'])
            if permission in system_permissions:
                return True
            
            # If project-specific permission is required
            if project_id and permission.startswith(('project:', 'task:', 'mcp:', 'agent:')):
                project_role = await self._get_project_role(user_id, project_id)
                if project_role:
                    project_permissions = RolePermissionMatrix.get_permissions(project_role)
                    return permission in project_permissions
            
            return False
        
        except Exception as e:
            await self.audit_logger.log_auth_event(
                user_id=user_id,
                action="permission_check_error",
                details={
                    "permission": permission,
                    "project_id": project_id,
                    "error": str(e)
                }
            )
            return False
    
    async def _get_project_role(self, user_id: str, project_id: str) -> Optional[str]:
        """Get user's role in specific project"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT role FROM project_members 
                WHERE user_id = $1 AND project_id = $2
                """,
                user_id, project_id
            )
            return result
    
    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        expires_hours: int = 24
    ) -> Dict[str, str]:
        """Create user session with tokens"""
        session_id = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_sessions (
                    id, user_id, session_token, refresh_token, 
                    ip_address, user_agent, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                session_id, user_id, session_id, refresh_token,
                ip_address, user_agent, expires_at
            )
        
        # Create JWT access token
        access_token = self._create_access_token({
            "sub": user_id,
            "session_id": session_id,
            "type": "access"
        })
        
        await self.audit_logger.log_auth_event(
            user_id=user_id,
            action="session_created",
            details={"session_id": session_id}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_hours * 3600
        }
    
    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate user session"""
        async with self.db_pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT s.*, u.id as user_id, u.email, u.username, u.role, u.status
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = $1 
                AND s.expires_at > CURRENT_TIMESTAMP
                AND s.is_active = TRUE
                AND u.status = 'active'
                """,
                session_token
            )
            
            if session:
                # Update last activity
                await conn.execute(
                    """
                    UPDATE user_sessions 
                    SET last_activity = CURRENT_TIMESTAMP 
                    WHERE id = $1
                    """,
                    session['id']
                )
                
                return dict(session)
        
        return None
    
    async def invalidate_session(self, session_token: str, user_id: str):
        """Invalidate user session"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE session_token = $1 AND user_id = $2
                """,
                session_token, user_id
            )
        
        await self.audit_logger.log_auth_event(
            user_id=user_id,
            action="session_invalidated",
            details={"session_token": session_token[:8] + "..."}
        )
    
    def _create_access_token(self, data: dict, expires_delta: timedelta = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=1)
        
        to_encode.update({"exp": expire})
        
        # Use a secure secret key (should be in environment variables)
        secret_key = "your-super-secret-jwt-key-change-in-production"
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
        return encoded_jwt
    
    def _decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT access token"""
        try:
            secret_key = "your-super-secret-jwt-key-change-in-production"
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None


class AuthenticationMiddleware:
    """Authentication middleware for FastAPI"""
    
    def __init__(self, rbac_manager: RBACManager):
        self.rbac_manager = rbac_manager
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request):
        """Authenticate request and add user context"""
        user_context = None
        
        # Try Bearer token authentication
        credentials: HTTPAuthorizationCredentials = await self.security(request)
        if credentials:
            payload = self.rbac_manager._decode_access_token(credentials.credentials)
            if payload:
                session = await self.rbac_manager.validate_session(payload.get("session_id"))
                if session:
                    user_context = {
                        "user_id": session["user_id"],
                        "email": session["email"],
                        "username": session["username"],
                        "role": session["role"],
                        "session_id": session["id"]
                    }
        
        # Try API key authentication as fallback
        if not user_context:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                key_info = await self.rbac_manager.validate_api_key(api_key)
                if key_info:
                    user_context = {
                        "user_id": key_info["user_id"],
                        "email": key_info["email"],
                        "username": key_info["username"],
                        "role": key_info["role"],
                        "api_key_id": key_info["api_key_id"],
                        "permissions": key_info["permissions"]
                    }
        
        # Add user context to request state
        request.state.user = user_context
        return user_context


def require_permission(permission: str, project_id_param: str = None):
    """Decorator to require specific permission"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Get user context
            user_context = getattr(request.state, 'user', None)
            if not user_context:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Get project ID if specified
            project_id = None
            if project_id_param:
                project_id = request.headers.get("X-Project-ID")
                if not project_id:
                    project_id = request.path_params.get(project_id_param)
            
            # Check permission
            rbac_manager = kwargs.get('rbac_manager')
            if not rbac_manager:
                # Try to get from global state or dependency injection
                from src.api.dependencies import get_rbac_manager
                rbac_manager = await get_rbac_manager()
            
            has_permission = await rbac_manager.check_permission(
                user_id=user_context["user_id"],
                permission=permission,
                project_id=project_id
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            # Add permission context to kwargs
            kwargs['permission_context'] = {
                'user_context': user_context,
                'permission': permission,
                'project_id': project_id
            }
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(required_role: str, project_based: bool = False):
    """Decorator to require specific role"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            user_context = getattr(request.state, 'user', None)
            if not user_context:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check role
            if project_based:
                project_id = request.headers.get("X-Project-ID")
                if not project_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Project ID required for project-based role check"
                    )
                
                # Get project role (implementation needed)
                rbac_manager = kwargs.get('rbac_manager')
                project_role = await rbac_manager._get_project_role(
                    user_context["user_id"], 
                    project_id
                )
                
                if not project_role or project_role != required_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Project role '{required_role}' required"
                    )
            else:
                if user_context["role"] != required_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"System role '{required_role}' required"
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global RBAC manager instance (will be initialized in main app)
_rbac_manager: Optional[RBACManager] = None

def init_rbac_manager(db_pool: asyncpg.Pool):
    """Initialize global RBAC manager"""
    global _rbac_manager
    _rbac_manager = RBACManager(db_pool)

def get_rbac_manager() -> RBACManager:
    """Get global RBAC manager instance"""
    if not _rbac_manager:
        raise RuntimeError("RBAC manager not initialized")
    return _rbac_manager


class RBACMiddleware:
    """ASGI Middleware for Role-Based Access Control"""
    
    def __init__(self, app):
        self.app = app
        import logging
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Create request object
        from starlette.requests import Request
        request = Request(scope, receive)
        
        # Try to authenticate user
        user_context = None
        
        try:
            # Check if RBAC manager is initialized
            if _rbac_manager:
                auth_middleware = AuthenticationMiddleware(_rbac_manager)
                user_context = await auth_middleware(request)
            else:
                self.logger.warning("RBAC manager not initialized, skipping authentication")
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            # Continue without authentication context
        
        # Add user context to request state
        if hasattr(request, 'state'):
            request.state.user = user_context
        
        # Continue to the application
        await self.app(scope, receive, send)
