"""
Database Manager for Kairos
Handles PostgreSQL connections, migrations, and database operations
"""

import asyncio
import asyncpg
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.db_url = self._get_database_url()
        
    def _get_database_url(self) -> str:
        """Get database URL from environment variables"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "kairos_user")
        password = os.getenv("POSTGRES_PASSWORD", "kairos_pass")
        database = os.getenv("POSTGRES_DB", "kairos_db")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize_database(self):
        """Initialize database connection pool and run migrations"""
        try:
            # Create connection pool
            self.db_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            logger.info("✅ Database connection pool created")
            
            # Run migrations
            await self._run_migrations()
            
            logger.info("🏗️ Database initialization completed")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _run_migrations(self):
        """Run database migrations"""
        try:
            migrations_dir = Path(__file__).parent / "migrations"
            if not migrations_dir.exists():
                logger.warning("📁 Migrations directory not found, skipping migrations")
                return
            
            # Get all migration files
            migration_files = sorted(migrations_dir.glob("*.sql"))
            
            async with self.db_pool.acquire() as conn:
                # Create migrations table if it doesn't exist
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Get applied migrations
                applied_migrations = await conn.fetch(
                    "SELECT version FROM schema_migrations"
                )
                applied_versions = {row['version'] for row in applied_migrations}
                
                # Apply new migrations
                for migration_file in migration_files:
                    version = migration_file.stem
                    
                    if version not in applied_versions:
                        logger.info(f"🔄 Applying migration: {version}")
                        
                        # Read and execute migration
                        migration_sql = migration_file.read_text(encoding='utf-8')
                        
                        try:
                            await conn.execute(migration_sql)
                            
                            # Record migration as applied
                            await conn.execute(
                                "INSERT INTO schema_migrations (version) VALUES ($1)",
                                version
                            )
                            
                            logger.info(f"✅ Migration applied: {version}")
                            
                        except Exception as e:
                            logger.error(f"❌ Migration failed: {version} - {e}")
                            raise
                    else:
                        logger.debug(f"⏭️ Migration already applied: {version}")
                        
        except Exception as e:
            logger.error(f"❌ Migration process failed: {e}")
            raise
    
    async def execute_query(self, query: str, *args):
        """Execute a database query"""
        if not self.db_pool:
            raise RuntimeError("Database not initialized")
            
        async with self.db_pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args):
        """Fetch one row from database"""
        if not self.db_pool:
            raise RuntimeError("Database not initialized")
            
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """Fetch all rows from database"""
        if not self.db_pool:
            raise RuntimeError("Database not initialized")
            
        async with self.db_pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def close(self):
        """Close database connections"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("🔒 Database connections closed")
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.db_pool is not None and not self.db_pool._closed
    
    async def health_check(self) -> dict:
        """Perform database health check"""
        if not self.db_pool:
            return {
                "status": "unhealthy",
                "error": "Database not initialized"
            }
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                
            return {
                "status": "healthy",
                "pool_size": len(self.db_pool._holders),
                "max_size": self.db_pool._maxsize,
                "min_size": self.db_pool._minsize
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global database manager instance
db_manager = DatabaseManager()
