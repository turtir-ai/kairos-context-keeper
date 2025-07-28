"""
User models for Kairos multi-user system
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets


class UserRole(Enum):
    """System-wide user roles"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class ProjectRole(Enum):
    """Project-specific roles"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class User:
    """User model with authentication and authorization"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def create_user(
        self, 
        email: str, 
        username: str, 
        password: str,
        first_name: str = "",
        last_name: str = "",
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.ACTIVE
    ) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                    id, email, username, password_hash, first_name, last_name,
                    role, status, created_at, last_login
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP, NULL)
                """,
                user_id, email.lower(), username, password_hash, 
                first_name, last_name, role.value, status.value
            )
        
        return user_id
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM users WHERE id = $1 AND status != 'deleted'""",
                user_id
            )
            
            if not row:
                return None
            
            return dict(row)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM users WHERE email = $1 AND status != 'deleted'""",
                email.lower()
            )
            
            if not row:
                return None
            
            return dict(row)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM users WHERE username = $1 AND status != 'deleted'""",
                username
            )
            
            if not row:
                return None
            
            return dict(row)
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        if not self._verify_password(password, user['password_hash']):
            return None
        
        if user['status'] != UserStatus.ACTIVE.value:
            return None
        
        # Update last login
        await self.update_last_login(user['id'])
        
        return user
    
    async def update_last_login(self, user_id: str):
        """Update user's last login timestamp"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1""",
                user_id
            )
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user information"""
        if not updates:
            return True
        
        # Filter allowed updates
        allowed_fields = {
            'first_name', 'last_name', 'email', 'username', 
            'role', 'status', 'profile_data'
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return True
        
        # Handle email normalization
        if 'email' in filtered_updates:
            filtered_updates['email'] = filtered_updates['email'].lower()
        
        # Handle password update separately
        if 'password' in updates:
            filtered_updates['password_hash'] = self._hash_password(updates['password'])
            filtered_updates.pop('password', None)
        
        # Handle profile_data JSON serialization
        if 'profile_data' in filtered_updates:
            filtered_updates['profile_data'] = json.dumps(filtered_updates['profile_data'])
        
        set_clauses = []
        values = []
        param_count = 1
        
        for field, value in filtered_updates.items():
            set_clauses.append(f"{field} = ${param_count}")
            values.append(value)
            param_count += 1
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        
        query = f"""
            UPDATE users 
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count}
        """
        
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(query, *values)
                return True
            except Exception as e:
                print(f"Error updating user: {e}")
                return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Soft delete user (set status to deleted)"""
        return await self.update_user(user_id, {'status': 'deleted'})
    
    async def list_users(
        self, 
        limit: int = 50, 
        offset: int = 0,
        role_filter: Optional[UserRole] = None,
        status_filter: Optional[UserStatus] = None
    ) -> List[Dict[str, Any]]:
        """List users with pagination and filters"""
        where_clauses = ["status != 'deleted'"]
        params = []
        param_count = 1
        
        if role_filter:
            where_clauses.append(f"role = ${param_count}")
            params.append(role_filter.value)
            param_count += 1
        
        if status_filter:
            where_clauses.append(f"status = ${param_count}")
            params.append(status_filter.value)
            param_count += 1
        
        params.extend([limit, offset])
        
        query = f"""
            SELECT id, email, username, first_name, last_name, role, status,
                   created_at, updated_at, last_login
            FROM users 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user with their roles"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT p.id, p.name, p.description, pm.role, pm.joined_at,
                       p.created_at, p.settings, p.is_active
                FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE pm.user_id = $1 AND p.is_active = TRUE
                ORDER BY pm.joined_at DESC
                """,
                user_id
            )
            
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "role": row["role"],
                    "joined_at": row["joined_at"].isoformat(),
                    "created_at": row["created_at"].isoformat(),
                    "settings": json.loads(row["settings"]) if row["settings"] else {},
                    "is_active": row["is_active"]
                }
                for row in rows
            ]
    
    async def add_to_project(
        self, 
        user_id: str, 
        project_id: str, 
        role: ProjectRole = ProjectRole.MEMBER
    ) -> bool:
        """Add user to project with specified role"""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO project_members (project_id, user_id, role)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (project_id, user_id)
                    DO UPDATE SET role = EXCLUDED.role, joined_at = CURRENT_TIMESTAMP
                    """,
                    project_id, user_id, role.value
                )
                return True
            except Exception as e:
                print(f"Error adding user to project: {e}")
                return False
    
    async def remove_from_project(self, user_id: str, project_id: str) -> bool:
        """Remove user from project"""
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """DELETE FROM project_members WHERE user_id = $1 AND project_id = $2""",
                    user_id, project_id
                )
                return True
            except Exception as e:
                print(f"Error removing user from project: {e}")
                return False
    
    async def has_permission(
        self, 
        user_id: str, 
        project_id: Optional[str] = None,
        required_role: str = "member"
    ) -> bool:
        """Check if user has required permission level"""
        user = await self.get_user(user_id)
        if not user:
            return False
        
        # Super admin has all permissions
        if user['role'] == UserRole.SUPER_ADMIN.value:
            return True
        
        # If no project specified, check system-wide role
        if not project_id:
            role_hierarchy = {
                UserRole.VIEWER.value: 1,
                UserRole.USER.value: 2,
                UserRole.ADMIN.value: 3,
                UserRole.SUPER_ADMIN.value: 4
            }
            user_level = role_hierarchy.get(user['role'], 0)
            required_level = role_hierarchy.get(required_role, 1)
            return user_level >= required_level
        
        # Check project-specific permission
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT has_project_access($1, $2, $3)",
                user_id, project_id, required_role
            )
            return result or False
    
    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2-SHA256"""
        salt = secrets.token_bytes(32)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ':' + pwdhash.hex()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt_hex, hash_hex = password_hash.split(':')
            salt = bytes.fromhex(salt_hex)
            stored_hash = bytes.fromhex(hash_hex)
            
            pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return pwdhash == stored_hash
        except Exception:
            return False
    
    async def create_api_key(
        self, 
        user_id: str, 
        name: str,
        permissions: List[str] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Create API key for user"""
        api_key = f"kairos_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        
        permissions = permissions or ["read", "write"]
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_keys (id, user_id, key_hash, name, permissions, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                key_id, user_id, self._hash_api_key(api_key), name,
                json.dumps(permissions), expires_at
            )
        
        return api_key
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return user info"""
        key_hash = self._hash_api_key(api_key)
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT ak.*, u.id as user_id, u.email, u.username, u.role, u.status
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE ak.key_hash = $1 
                AND ak.is_active = TRUE
                AND u.status = 'active'
                AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)
                """,
                key_hash
            )
            
            if not row:
                return None
            
            # Update last used timestamp
            await conn.execute(
                """UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE id = $1""",
                row['id']
            )
            
            return {
                'api_key_id': row['id'],
                'user_id': row['user_id'],
                'email': row['email'],
                'username': row['username'],
                'role': row['role'],
                'status': row['status'],
                'permissions': json.loads(row['permissions']) if row['permissions'] else [],
                'name': row['name']
            }
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
