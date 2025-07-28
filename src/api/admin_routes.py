"""
Admin API Routes for Team Management
Provides comprehensive team management functionality including invitations and audit logs
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from pydantic import BaseModel, EmailStr, validator
from api.rbac_middleware import (
    RBACManager, Permission, require_permission, require_role,
    get_rbac_manager, AuthenticationMiddleware
)
from database.models.user import User, UserRole, ProjectRole, UserStatus
from database.models.audit import AuditLogger, AuditEventType, AuditSeverity

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request/response validation
class UserInvitation(BaseModel):
    email: EmailStr
    firstName: str = ""
    lastName: str = ""
    role: str = "user"
    message: str = ""
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = ['super_admin', 'admin', 'user', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class UserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = ['super_admin', 'admin', 'user', 'viewer']
            if v not in valid_roles:
                raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['active', 'inactive', 'pending', 'suspended']
            if v not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class UserWithProjectCount(BaseModel):
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
    project_count: int


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    invited_by_name: str
    created_at: str
    expires_at: str


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    username: Optional[str]
    email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    success: bool
    ip_address: Optional[str]
    error_message: Optional[str]


# Dependency to get current admin user
async def get_current_admin_user(
    request: Request,
    rbac_manager: RBACManager = Depends(get_rbac_manager)
) -> Dict[str, Any]:
    """Get current authenticated admin user"""
    user_context = getattr(request.state, 'user', None)
    if not user_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Check if user has admin permissions
    has_admin_permission = await rbac_manager.check_permission(
        user_id=user_context['user_id'],
        permission=Permission.SYSTEM_ADMIN
    )
    
    if not has_admin_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    
    return user_context


# User management endpoints
@router.get("/users")
async def get_all_users(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Get all users with project counts (admin only)"""
    try:
        # Get users
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
        
        # Get project counts for each user
        users_with_counts = []
        for user in users:
            projects = await rbac_manager.user_model.get_user_projects(user['id'])
            user_data = UserWithProjectCount(
                id=user['id'],
                email=user['email'],
                username=user['username'],
                first_name=user['first_name'] or '',
                last_name=user['last_name'] or '',
                role=user['role'],
                status=user['status'],
                created_at=user['created_at'].isoformat(),
                last_login=user['last_login'].isoformat() if user['last_login'] else None,
                email_verified=user.get('email_verified', False),
                project_count=len(projects)
            )
            users_with_counts.append(user_data)
        
        return {"users": users_with_counts}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.post("/invite")
async def invite_user(
    request: Request,
    invitation_data: UserInvitation,
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Send user invitation"""
    try:
        # Check if user already exists
        existing_user = await rbac_manager.user_model.get_user_by_email(invitation_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create invitation record
        invitation_id = str(uuid.uuid4())
        invitation_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
        
        async with rbac_manager.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_invitations (
                    id, email, first_name, last_name, role, 
                    invited_by, invitation_token, message, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                invitation_id, invitation_data.email.lower(),
                invitation_data.firstName, invitation_data.lastName,
                invitation_data.role, current_user['user_id'],
                invitation_token, invitation_data.message, expires_at
            )
        
        # Log invitation
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.USER_INVITED,
            user_id=current_user['user_id'],
            severity=AuditSeverity.MEDIUM,
            details={
                "invited_email": invitation_data.email,
                "role": invitation_data.role,
                "invitation_id": invitation_id
            },
            ip_address=request.client.host if request.client else None
        )
        
        # TODO: Send invitation email
        # In a real implementation, you would send an email with the invitation link
        # containing the invitation_token
        
        return {
            "message": "Invitation sent successfully",
            "invitation_id": invitation_id,
            "expires_at": expires_at.isoformat()
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invitation: {str(e)}"
        )


@router.get("/invitations")
async def get_invitations(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Get pending invitations"""
    try:
        async with rbac_manager.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT i.*, u.first_name || ' ' || u.last_name as invited_by_name
                FROM user_invitations i
                JOIN users u ON i.invited_by = u.id
                WHERE i.status = 'pending' AND i.expires_at > CURRENT_TIMESTAMP
                ORDER BY i.created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            
            invitations = [
                InvitationResponse(
                    id=row['id'],
                    email=row['email'],
                    role=row['role'],
                    status=row['status'],
                    invited_by_name=row['invited_by_name'],
                    created_at=row['created_at'].isoformat(),
                    expires_at=row['expires_at'].isoformat()
                )
                for row in rows
            ]
        
        return {"invitations": invitations}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invitations: {str(e)}"
        )


@router.put("/users/{user_id}")
async def update_user(
    request: Request,
    user_id: str,
    user_update: UserUpdate,
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Update user information"""
    try:
        # Prevent non-super-admins from updating super-admin users
        target_user = await rbac_manager.user_model.get_user(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Only super-admins can modify super-admins
        if target_user['role'] == 'super_admin' and current_user.get('role') != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify super admin users"
            )
        
        # Prepare update data
        update_data = {}
        if user_update.firstName is not None:
            update_data['first_name'] = user_update.firstName
        if user_update.lastName is not None:
            update_data['last_name'] = user_update.lastName
        if user_update.email is not None:
            update_data['email'] = user_update.email
        if user_update.role is not None:
            update_data['role'] = user_update.role
        if user_update.status is not None:
            update_data['status'] = user_update.status
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        # Update user
        success = await rbac_manager.user_model.update_user(user_id, update_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        # Log user update
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.USER_UPDATED,
            user_id=current_user['user_id'],
            severity=AuditSeverity.MEDIUM,
            details={
                "target_user_id": user_id,
                "updated_fields": list(update_data.keys()),
                "changes": update_data
            },
            ip_address=request.client.host if request.client else None
        )
        
        return {"message": "User updated successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Delete user (soft delete)"""
    try:
        # Prevent deletion of super-admin users by non-super-admins
        target_user = await rbac_manager.user_model.get_user(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-deletion
        if user_id == current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Only super-admins can delete super-admins
        if target_user['role'] == 'super_admin' and current_user.get('role') != 'super_admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete super admin users"
            )
        
        # Soft delete user
        success = await rbac_manager.user_model.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        # Log user deletion
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.USER_DELETED,
            user_id=current_user['user_id'],
            severity=AuditSeverity.HIGH,
            details={
                "deleted_user_id": user_id,
                "deleted_user_email": target_user['email']
            },
            ip_address=request.client.host if request.client else None
        )
        
        return {"message": "User deleted successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Get audit logs"""
    try:
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        logs = await rbac_manager.audit_logger.get_audit_logs(
            user_id=user_id,
            event_type=event_type_enum,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        audit_logs = [
            AuditLogResponse(
                id=log['id'],
                timestamp=log['timestamp'],
                username=log.get('username'),
                email=log.get('email'),
                action=log['event_type'],
                resource_type=log.get('resource_type'),
                resource_id=log.get('resource_id'),
                success=log['success'],
                ip_address=log.get('ip_address'),
                error_message=log.get('error_message')
            )
            for log in logs
        ]
        
        return {"logs": audit_logs}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


@router.post("/resend-invitation/{invitation_id}")
async def resend_invitation(
    request: Request,
    invitation_id: str,
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Resend user invitation"""
    try:
        async with rbac_manager.db_pool.acquire() as conn:
            # Get invitation
            invitation = await conn.fetchrow(
                "SELECT * FROM user_invitations WHERE id = $1 AND status = 'pending'",
                invitation_id
            )
            
            if not invitation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found or already used"
                )
            
            # Extend expiry date
            new_expires_at = datetime.utcnow() + timedelta(days=7)
            await conn.execute(
                "UPDATE user_invitations SET expires_at = $1 WHERE id = $2",
                new_expires_at, invitation_id
            )
        
        # Log invitation resend
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.INVITATION_RESENT,
            user_id=current_user['user_id'],
            severity=AuditSeverity.LOW,
            details={
                "invitation_id": invitation_id,
                "email": invitation['email']
            },
            ip_address=request.client.host if request.client else None
        )
        
        # TODO: Resend invitation email
        
        return {
            "message": "Invitation resent successfully",
            "expires_at": new_expires_at.isoformat()
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend invitation: {str(e)}"
        )


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    request: Request,
    invitation_id: str,
    current_user: Dict = Depends(get_current_admin_user),
    rbac_manager: RBACManager = Depends(get_rbac_manager)
):
    """Cancel pending invitation"""
    try:
        async with rbac_manager.db_pool.acquire() as conn:
            # Update invitation status
            result = await conn.execute(
                "UPDATE user_invitations SET status = 'cancelled' WHERE id = $1 AND status = 'pending'",
                invitation_id
            )
            
            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invitation not found or already processed"
                )
        
        # Log invitation cancellation
        await rbac_manager.audit_logger.log_event(
            event_type=AuditEventType.INVITATION_CANCELLED,
            user_id=current_user['user_id'],
            severity=AuditSeverity.LOW,
            details={"invitation_id": invitation_id},
            ip_address=request.client.host if request.client else None
        )
        
        return {"message": "Invitation cancelled successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel invitation: {str(e)}"
        )


# Health check endpoint
@router.get("/health")
async def admin_health_check():
    """Health check for admin service"""
    return {
        "status": "healthy",
        "service": "kairos-admin",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
