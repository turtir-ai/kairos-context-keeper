"""
FastAPI Dependencies for Authentication and RBAC
Provides dependency injection for authentication and authorization
"""

from typing import Dict, Optional, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.rbac_middleware import RBACManager, get_rbac_manager
from database.models.user import UserStatus

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    request: Request,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None"""
    return getattr(request.state, 'user', None)


async def get_current_user_required(
    request: Request,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
) -> Dict[str, Any]:
    """Get current user (authentication required)"""
    user_context = getattr(request.state, 'user', None)
    if not user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_context


async def get_current_active_user(
    current_user: Dict = Depends(get_current_user_required),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
) -> Dict[str, Any]:
    """Get current user and ensure they are active"""
    # Get full user details to check status
    user = await rbac_manager.user_model.get_user(current_user['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user['status'] != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user['status']}"
        )
    
    return current_user


async def get_current_project_id(request: Request) -> Optional[str]:
    """Extract project ID from request headers or path"""
    # Try header first
    project_id = request.headers.get("X-Project-ID")
    if project_id:
        return project_id
    
    # Try path parameters
    if hasattr(request, 'path_params'):
        return request.path_params.get('project_id')
    
    return None


class PermissionChecker:
    """Dependency class for checking specific permissions"""
    
    def __init__(self, permission: str, project_required: bool = False):
        self.permission = permission
        self.project_required = project_required
    
    async def __call__(
        self,
        request: Request,
        current_user: Dict = Depends(get_current_active_user),
        rbac_manager: RBACManager = Depends(get_rbac_manager)
    ) -> Dict[str, Any]:
        """Check if current user has required permission"""
        project_id = None
        
        if self.project_required:
            project_id = await get_current_project_id(request)
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project ID required for this operation"
                )
        
        has_permission = await rbac_manager.check_permission(
            user_id=current_user['user_id'],
            permission=self.permission,
            project_id=project_id
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{self.permission}' required"
            )
        
        return {
            'user_context': current_user,
            'permission': self.permission,
            'project_id': project_id
        }


class RoleChecker:
    """Dependency class for checking user roles"""
    
    def __init__(self, required_role: str, project_based: bool = False):
        self.required_role = required_role
        self.project_based = project_based
    
    async def __call__(
        self,
        request: Request,
        current_user: Dict = Depends(get_current_active_user),
        rbac_manager: RBACManager = Depends(get_rbac_manager)
    ) -> Dict[str, Any]:
        """Check if current user has required role"""
        if self.project_based:
            project_id = await get_current_project_id(request)
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project ID required for project-based role check"
                )
            
            # Get user's project role
            project_role = await rbac_manager._get_project_role(
                current_user['user_id'], 
                project_id
            )
            
            if not project_role or project_role != self.required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Project role '{self.required_role}' required"
                )
            
            return {
                'user_context': current_user,
                'project_role': project_role,
                'project_id': project_id
            }
        else:
            # Check system-wide role
            if current_user['role'] != self.required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"System role '{self.required_role}' required"
                )
            
            return {
                'user_context': current_user,
                'system_role': current_user['role']
            }


class ProjectAccessChecker:
    """Dependency class for checking project access"""
    
    def __init__(self, required_role: str = "member"):
        self.required_role = required_role
    
    async def __call__(
        self,
        request: Request,
        current_user: Dict = Depends(get_current_active_user),
        rbac_manager: RBACManager = Depends(get_rbac_manager)
    ) -> Dict[str, Any]:
        """Check if user has access to project with required role"""
        project_id = await get_current_project_id(request)
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project ID required"
            )
        
        # Check project access using the function from auth.py
        from api.auth import project_manager
        has_access = await project_manager.check_project_access(
            current_user['user_id'], 
            project_id, 
            self.required_role
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project access with role '{self.required_role}' required"
            )
        
        return {
            'user_context': current_user,
            'project_id': project_id,
            'required_role': self.required_role
        }


# Common permission dependencies
def require_system_admin():
    """Require super_admin role"""
    return RoleChecker("super_admin")


def require_admin():
    """Require admin or super_admin role"""
    return RoleChecker("admin")


def require_project_owner():
    """Require owner role in project"""
    return RoleChecker("owner", project_based=True)


def require_project_admin():
    """Require admin+ role in project"""
    return RoleChecker("admin", project_based=True)


def require_project_member():
    """Require member+ role in project"""
    return ProjectAccessChecker("member")


def require_project_viewer():
    """Require viewer+ role in project"""
    return ProjectAccessChecker("viewer")


# Permission-based dependencies
def require_system_read():
    """Require system:read permission"""
    return PermissionChecker("system:read")


def require_system_write():
    """Require system:write permission"""
    return PermissionChecker("system:write")


def require_project_read():
    """Require project:read permission"""
    return PermissionChecker("project:read", project_required=True)


def require_project_write():
    """Require project:write permission"""
    return PermissionChecker("project:write", project_required=True)


def require_task_create():
    """Require task:create permission"""
    return PermissionChecker("task:create", project_required=True)


def require_task_execute():
    """Require task:execute permission"""
    return PermissionChecker("task:execute", project_required=True)


def require_mcp_execute():
    """Require mcp:execute permission"""
    return PermissionChecker("mcp:execute", project_required=True)


def require_agent_execute():
    """Require agent:execute permission"""
    return PermissionChecker("agent:execute", project_required=True)


# Initialization function
async def init_dependencies(db_pool):
    """Initialize all dependencies with database pool"""
    from api.rbac_middleware import init_rbac_manager
    from api.auth import project_manager
    
    init_rbac_manager(db_pool)
    await project_manager.init_db_pool(db_pool)
    
    return True


# Utility functions for manual permission checking
async def check_user_permission(
    user_id: str,
    permission: str,
    project_id: Optional[str] = None,
    rbac_manager: RBACManager = None
) -> bool:
    """Utility function to check user permission programmatically"""
    if not rbac_manager:
        rbac_manager = get_rbac_manager()
    
    return await rbac_manager.check_permission(
        user_id=user_id,
        permission=permission,
        project_id=project_id
    )


async def get_user_project_role(
    user_id: str,
    project_id: str,
    rbac_manager: RBACManager = None
) -> Optional[str]:
    """Get user's role in specific project"""
    if not rbac_manager:
        rbac_manager = get_rbac_manager()
    
    return await rbac_manager._get_project_role(user_id, project_id)


async def validate_project_access(
    user_id: str,
    project_id: str,
    required_role: str = "member",
    rbac_manager: RBACManager = None
) -> bool:
    """Validate user has required access to project"""
    if not rbac_manager:
        rbac_manager = get_rbac_manager()
    
    from api.auth import project_manager
    return await project_manager.check_project_access(
        user_id, 
        project_id, 
        required_role
    )
