"""
Simple project manager for Kairos multi-user system
"""

import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import HTTPException
import asyncpg


class ProjectManager:
    """Manages multi-project functionality"""
    
    def __init__(self):
        self.db_pool = None
    
    async def init_db_pool(self, db_pool):
        """Initialize database pool"""
        self.db_pool = db_pool
    
    async def create_project(self, name: str, description: str, owner_id: str, settings: Dict = None) -> str:
        """Create a new project"""
        if not self.db_pool:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        project_id = str(uuid.uuid4())
        settings = settings or {}
        
        async with self.db_pool.acquire() as conn:
            try:
                # Create project
                await conn.execute(
                    """
                    INSERT INTO projects (id, name, description, settings)
                    VALUES ($1, $2, $3, $4)
                    """,
                    project_id, name, description, json.dumps(settings)
                )
                
                # Add owner as project member
                await conn.execute(
                    """
                    INSERT INTO project_members (project_id, user_id, role)
                    VALUES ($1, $2, 'owner')
                    """,
                    project_id, owner_id
                )
                
                return project_id
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
    
    async def get_project(self, project_id: str, user_id: str) -> Optional[Dict]:
        """Get project details if user has access"""
        if not self.db_pool:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT p.id, p.name, p.description, pm.role,
                       p.created_at, p.updated_at, p.settings, p.is_active
                FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE p.id = $1 AND pm.user_id = $2 AND p.is_active = TRUE
                """,
                project_id, user_id
            )
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "role": row["role"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "settings": json.loads(row["settings"]) if row["settings"] else {},
                "is_active": row["is_active"]
            }
    
    async def check_project_access(self, user_id: str, project_id: str, required_role: str = "member") -> bool:
        """Check if user has required access to project"""
        if not self.db_pool:
            return False
        
        # Simple role hierarchy check
        role_hierarchy = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}
        required_level = role_hierarchy.get(required_role, 1)
        
        async with self.db_pool.acquire() as conn:
            user_role = await conn.fetchval(
                "SELECT role FROM project_members WHERE user_id = $1 AND project_id = $2",
                user_id, project_id
            )
            
            if not user_role:
                return False
            
            user_level = role_hierarchy.get(user_role, 0)
            return user_level >= required_level


# Global project manager instance
project_manager = ProjectManager()
