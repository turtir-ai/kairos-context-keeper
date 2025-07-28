"""
Database utilities for Kairos
Handles database connections and common operations
"""

import os
import asyncio
import asyncpg
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://kairos:kairos123@localhost:5432/kairos_db"
        )
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Database connection pool initialized")
            
            # Create tables if they don't exist
            await self.create_tables()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            # Don't raise - allow system to run without database
            
    async def create_tables(self):
        """Create necessary database tables"""
        if not self.pool:
            return
            
        try:
            async with self.pool.acquire() as conn:
                # Create fine-tuning dataset table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS fine_tuning_dataset (
                        id SERIAL PRIMARY KEY,
                        task_id VARCHAR(255) UNIQUE NOT NULL,
                        project_id VARCHAR(255),
                        prompt TEXT NOT NULL,
                        failed_output TEXT,
                        corrected_output TEXT,
                        failure_reason VARCHAR(100),
                        guardian_feedback TEXT,
                        error_details TEXT,
                        model_key VARCHAR(255),
                        task_type VARCHAR(100),
                        is_approved BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create model performance metrics table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS model_performance_metrics (
                        id SERIAL PRIMARY KEY,
                        model_key VARCHAR(255) NOT NULL,
                        task_type VARCHAR(100) NOT NULL,
                        execution_time_ms INTEGER,
                        success BOOLEAN,
                        token_count INTEGER,
                        cost_estimate DECIMAL(10, 6),
                        error_type VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_model_task (model_key, task_type)
                    )
                """)
                
                logger.info("✅ Database tables created/verified")
                
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
            
    async def execute(self, query: str, *args):
        """Execute a database query"""
        if not self.pool:
            logger.warning("Database not available - skipping query")
            return None
            
        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database query error: {e}")
            raise
            
    async def fetch(self, query: str, *args):
        """Fetch results from database"""
        if not self.pool:
            logger.warning("Database not available - returning empty results")
            return []
            
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *args)
        except Exception as e:
            logger.error(f"Database fetch error: {e}")
            return []
            
    async def fetchrow(self, query: str, *args):
        """Fetch single row from database"""
        if not self.pool:
            logger.warning("Database not available - returning None")
            return None
            
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            logger.error(f"Database fetchrow error: {e}")
            return None


# Global database manager instance
db_manager = DatabaseManager()
