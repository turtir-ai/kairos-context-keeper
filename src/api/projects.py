"""
Project management API endpoints for Kairos
Handles creation, management, and access control for multi-project architecture
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse

from .auth import (
    require_auth, verify_api_key, project_manager, 
    get_current_project, require_project_access
)

# Pydantic models for request/response
class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Project settings")

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[Dict[str, Any]] = None

class ProjectMemberRequest(BaseModel):
    user_id: str = Field(..., description="User ID to add to project")
    role: str = Field(..., pattern="^(viewer|member|admin|owner)$", description="User role in project")

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    role: str
    created_at: str
    updated_at: Optional[str]
    settings: Dict[str, Any]
    is_active: bool

class ProjectListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    role: str
    joined_at: str
    created_at: str
    settings: Dict[str, Any]
    is_active: bool

# Create router
router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=Dict[str, str])
@require_auth(permissions=["write"])
async def create_project(
    project_data: ProjectCreateRequest,
    request: Request,
    auth_info: Dict = None
):
    """
    Create a new project
    
    Creates a new isolated project workspace and adds the creator as the owner.
    Each project has its own data isolation and access control.
    """
    try:
        user_id = auth_info["api_key"]  # Using API key as user ID for now
        
        project_id = await project_manager.create_project(
            name=project_data.name,
            description=project_data.description,
            owner_id=user_id,
            settings=project_data.settings
        )
        
        return {
            "project_id": project_id,
            "message": f"Project '{project_data.name}' created successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("/", response_model=List[ProjectListResponse])
@require_auth(permissions=["read"])
async def list_user_projects(
    request: Request,
    auth_info: Dict = None
):
    """
    Get all projects accessible to the current user
    
    Returns a list of all projects where the user is a member,
    along with their role in each project.
    """
    try:
        user_id = auth_info["api_key"]
        projects = await project_manager.get_user_projects(user_id)
        
        return [ProjectListResponse(**project) for project in projects]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
@require_auth(permissions=["read"])
async def get_project(
    project_id: str,
    request: Request,
    auth_info: Dict = None
):
    """
    Get detailed information about a specific project
    
    Returns project details if the user has access to the project.
    """
    try:
        user_id = auth_info["api_key"]
        project = await project_manager.get_project(project_id, user_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return ProjectResponse(**project)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )

@router.put("/{project_id}")
@require_auth(permissions=["write"])
async def update_project(
    project_id: str,
    updates: ProjectUpdateRequest,
    request: Request,
    auth_info: Dict = None
):
    """
    Update project settings
    
    Updates project information. Requires admin or owner role in the project.
    """
    try:
        user_id = auth_info["api_key"]
        
        # Convert to dict, removing None values
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid updates provided"
            )
        
        success = await project_manager.update_project(project_id, user_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project"
            )
        
        return {"message": "Project updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )

@router.post("/{project_id}/members")
@require_auth(permissions=["write"])
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberRequest,
    request: Request,
    auth_info: Dict = None
):
    """
    Add a member to the project
    
    Adds a user to the project with the specified role.
    Requires admin or owner role in the project.
    """
    try:
        requester_id = auth_info["api_key"]
        
        success = await project_manager.add_project_member(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role,
            requester_id=requester_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add project member"
            )
        
        return {"message": f"User {member_data.user_id} added to project with role {member_data.role}"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project member: {str(e)}"
        )

@router.get("/{project_id}/access-check")
@require_auth(permissions=["read"])
async def check_project_access(
    project_id: str,
    request: Request,
    role: str = "member",
    auth_info: Dict = None
):
    """
    Check if current user has required access to project
    
    Useful for frontend applications to determine what actions are available.
    """
    try:
        user_id = auth_info["api_key"]
        has_access = await project_manager.check_project_access(user_id, project_id, role)
        
        return {
            "has_access": has_access,
            "user_id": user_id,
            "project_id": project_id,
            "required_role": role
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check project access: {str(e)}"
        )

@router.post("/{project_id}/switch")
@require_auth(permissions=["read"])
async def switch_to_project(
    project_id: str,
    request: Request,
    auth_info: Dict = None
):
    """
    Switch user's active project context
    
    Returns a new JWT token with the specified project context.
    The user must have access to the project.
    """
    try:
        from .auth import create_access_token
        
        user_id = auth_info["api_key"]
        
        # Verify user has access to project
        has_access = await project_manager.check_project_access(user_id, project_id, "member")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to project"
            )
        
        # Create new token with project context
        token_data = {"sub": user_id}
        access_token = create_access_token(data=token_data, project_id=project_id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "project_id": project_id,
            "message": f"Switched to project {project_id}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch project: {str(e)}"
        )

# Health check for project system
@router.get("/health/check")
async def project_system_health():
    """
    Check if project management system is healthy
    """
    try:
        # Basic health check - verify database connection
        if not project_manager.db_pool:
            return {
                "status": "unhealthy",
                "message": "Database not initialized"
            }
        
        # Try a simple query
        async with project_manager.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "message": "Project management system operational"
        }
    
    except Exception as e:
        return {
            "status": "unhealthy", 
            "message": f"Database connection failed: {str(e)}"
        }
