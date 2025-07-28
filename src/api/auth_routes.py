"""
Multi-user Authentication API Routes for Kairos
Provides comprehensive user management, authentication, and project access
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, status, Depends, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from api.rbac_middleware import (
    RBACManager, Permission, require_permission, require_role,
    get_rbac_manager, AuthenticationMiddleware
)
from database.models.user import User, UserRole, ProjectRole, UserStatus
from database.models.audit import AuditLogger

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


# Pydantic models for request/response validation
class UserRegistration(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: str = ""
    last_name: str = ""

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    role: str
    status: str
    created_at: str
    last_login: Optional[str]
    email_verified: bool


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    role: str
    joined_at: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse


class ApiKeyRequest(BaseModel):
    name: str
    permissions: List[str] = ["read", "write"]
    expires_days: Optional[int] = None
    project_id: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    permissions: List[str]
    expires_at: Optional[str]
    created_at: str


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    visibility: str = "private"

    @validator('visibility')
    def validate_visibility(cls, v):
        if v not in ['public', 'private', 'internal']:
            raise ValueError('Visibility must be public, private, or internal')
        return v


class ProjectMemberRequest(BaseModel):
    user_id: str
    role: str = "member"

    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['owner', 'admin', 'member', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


# Dependency to get current user
async def get_current_user(
    request: Request,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
) -> Dict[str, Any]:
    """Get current authenticated user"""
    user_context = getattr(request.state, 'user', None)
    if not user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_context


# Authentication endpoints
@router.post("/register", response_model=UserResponse)
async def register_user(
    request: Request,
    user_data: UserRegistration,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await rbac_manager.user_model.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        existing_username = await rbac_manager.user_model.get_user_by_username(user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user_id = await rbac_manager.user_model.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        # Get created user
        user = await rbac_manager.user_model.get_user(user_id)
        
        # Log registration
        from database.models.audit import AuditEventType, AuditSeverity
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.USER_CREATED,
            user_id=user_id,
            severity=AuditSeverity.MEDIUM,
            details={"email": user_data.email, "username": user_data.username},
            ip_address=request.client.host if request.client else None
        )
        
        return UserResponse(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=user['role'],
            status=user['status'],
            created_at=user['created_at'].isoformat(),
            last_login=user['last_login'].isoformat() if user['last_login'] else None,
            email_verified=user['email_verified']
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    login_data: UserLogin,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Authenticate user and return access token"""
    try:
        # Authenticate user
        user = await rbac_manager.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create session
        session_hours = 24 * 7 if login_data.remember_me else 24  # 7 days or 1 day
        token_data = await rbac_manager.create_session(
            user_id=user['id'],
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            expires_hours=session_hours
        )
        
        user_response = UserResponse(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            role=user['role'],
            status=user['status'],
            created_at=user['created_at'].isoformat(),
            last_login=user['last_login'].isoformat() if user['last_login'] else None,
            email_verified=user['email_verified']
        )
        
        return TokenResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=user_response
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Logout user and invalidate session"""
    try:
        session_id = current_user.get('session_id')
        if session_id:
            await rbac_manager.invalidate_session(session_id, current_user['user_id'])
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


# User management endpoints
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Get current user information"""
    user = await rbac_manager.user_model.get_user(current_user['user_id'])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user['id'],
        email=user['email'],
        username=user['username'],
        first_name=user['first_name'],
        last_name=user['last_name'],
        role=user['role'],
        status=user['status'],
        created_at=user['created_at'].isoformat(),
        last_login=user['last_login'].isoformat() if user['last_login'] else None,
        email_verified=user['email_verified']
    )


@router.get("/users", response_model=List[UserResponse])
@require_permission(Permission.SYSTEM_READ)
async def list_users(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """List all users (admin only)"""
    try:
        role_enum = None
        if role_filter:
            try:
                role_enum = UserRole(role_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role filter: {role_filter}"
                )
        
        status_enum = None
        if status_filter:
            try:
                status_enum = UserStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )
        
        users = await rbac_manager.user_model.list_users(
            limit=limit,
            offset=offset,
            role_filter=role_enum,
            status_filter=status_enum
        )
        
        return [
            UserResponse(
                id=user['id'],
                email=user['email'],
                username=user['username'],
                first_name=user['first_name'],
                last_name=user['last_name'],
                role=user['role'],
                status=user['status'],
                created_at=user['created_at'].isoformat(),
                last_login=user['last_login'].isoformat() if user['last_login'] else None,
                email_verified=user.get('email_verified', False)
            )
            for user in users
        ]
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


# Project management endpoints
@router.post("/projects", response_model=ProjectResponse)
@require_permission(Permission.PROJECT_CREATE)
async def create_project(
    request: Request,
    project_data: ProjectCreateRequest,
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Create a new project"""
    try:
        # Use the project manager from auth.py
        from api.auth import project_manager
        
        project_id = await project_manager.create_project(
            name=project_data.name,
            description=project_data.description,
            owner_id=current_user['user_id'],
            settings={"visibility": project_data.visibility}
        )
        
        # Log project creation
        await rbac_manager.audit_logger.log_auth_event(
            user_id=current_user['user_id'],
            action="project_created",
            details={"project_id": project_id, "name": project_data.name}
        )
        
        # Get created project
        project = await project_manager.get_project(project_id, current_user['user_id'])
        
        return ProjectResponse(
            id=project['id'],
            name=project['name'],
            description=project['description'],
            role=project['role'],
            joined_at=project['created_at'],
            is_active=project['is_active']
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Get all projects for current user"""
    try:
        projects = await rbac_manager.user_model.get_user_projects(current_user['user_id'])
        
        return [
            ProjectResponse(
                id=project['id'],
                name=project['name'],
                description=project['description'],
                role=project['role'],
                joined_at=project['joined_at'],
                is_active=project['is_active']
            )
            for project in projects
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get projects: {str(e)}"
        )


# API Key management endpoints
@router.post("/api-keys", response_model=ApiKeyResponse)
@require_permission(Permission.API_KEY_CREATE)
async def create_api_key(
    request: Request,
    key_data: ApiKeyRequest,
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Create a new API key"""
    try:
        expires_at = None
        if key_data.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)
        
        api_key = await rbac_manager.user_model.create_api_key(
            user_id=current_user['user_id'],
            name=key_data.name,
            permissions=key_data.permissions,
            expires_at=expires_at
        )
        
        # Log API key creation
        await rbac_manager.audit_logger.log_auth_event(
            user_id=current_user['user_id'],
            action="api_key_created",
            details={"name": key_data.name, "permissions": key_data.permissions}
        )
        
        return ApiKeyResponse(
            id="generated",  # Don't expose internal ID
            name=key_data.name,
            key=api_key,
            permissions=key_data.permissions,
            expires_at=expires_at.isoformat() if expires_at else None,
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def auth_health_check():
    """Health check for authentication service"""
    return {
        "status": "healthy",
        "service": "kairos-auth",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


# Admin endpoints
@router.post("/admin/users/{user_id}/role")
@require_role("super_admin")
async def update_user_role(
    request: Request,
    user_id: str,
    new_role: str = Form(...),
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Update user role (super admin only)"""
    try:
        # Validate role
        try:
            UserRole(new_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {new_role}"
            )
        
        # Update user role
        success = await rbac_manager.user_model.update_user(
            user_id=user_id,
            updates={"role": new_role}
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )
        
        # Log role update
        await rbac_manager.audit_logger.log_auth_event(
            user_id=current_user['user_id'],
            action="user_role_updated",
            details={
                "target_user_id": user_id,
                "new_role": new_role
            }
        )
        
        return {"message": f"User role updated to {new_role}"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user role: {str(e)}"
        )


@router.post("/admin/users/{user_id}/status")
@require_role("super_admin")
async def update_user_status(
    request: Request,
    user_id: str,
    new_status: str = Form(...),
    current_user: Dict = Depends(get_current_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Update user status (super admin only)"""
    try:
        # Validate status
        try:
            UserStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status}"
            )
        
        # Update user status
        success = await rbac_manager.user_model.update_user(
            user_id=user_id,
            updates={"status": new_status}
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or update failed"
            )
        
        # Log status update
        await rbac_manager.audit_logger.log_auth_event(
            user_id=current_user['user_id'],
            action="user_status_updated",
            details={
                "target_user_id": user_id,
                "new_status": new_status
            }
        )
        
        return {"message": f"User status updated to {new_status}"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user status: {str(e)}"
        )
