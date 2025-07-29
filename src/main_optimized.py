"""
Phase 3: Complex Function Refactoring - Main Application Optimization
Breaking down the large startup_logic function into smaller, manageable components.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KairosApplicationBuilder:
    """Builder class for constructing the Kairos application with optimized startup"""
    
    def __init__(self):
        self.app = None
        self.config = None
        self.middleware_components = {}
        self.initialized_services = {}
        
    def build_application(self) -> FastAPI:
        """Main application builder with optimized component loading"""
        # Step 1: Load configuration
        self._load_configuration()
        
        # Step 2: Create FastAPI application
        self._create_fastapi_app()
        
        # Step 3: Add middleware components
        self._setup_middleware()
        
        # Step 4: Setup routes
        self._setup_routes()
        
        # Step 5: Setup startup events
        self._setup_startup_events()
        
        logger.info("🚀 Kairos application built successfully")
        return self.app
    
    def _load_configuration(self):
        """Load application configuration with fallback handling"""
        try:
            from src.core.config import get_config
            config_obj = get_config()
            self.config = self._build_config_dict(config_obj)
            logger.info("✅ Configuration loaded from core config")
        except ImportError as e:
            logger.warning(f"Core config not available: {e}")
            self.config = self._get_fallback_config()
    
    def _build_config_dict(self, config_obj) -> Dict[str, Any]:
        """Build configuration dictionary from config object"""
        return {
            "app": {
                "title": "Kairos: The Context Keeper",
                "description": "Autonomous development supervisor powered by context engineering",
                "version": "1.0.0",
                "debug": getattr(config_obj.server, 'debug', False),
                "cors_origins": getattr(config_obj.server, 'cors_origins', ["*"])
            },
            "database": {
                "url": getattr(config_obj.database, 'database_url', "sqlite:///kairos.db"),
                "pool_size": 10
            },
            "server": {
                "host": getattr(config_obj.server, 'host', "0.0.0.0"),
                "port": getattr(config_obj.server, 'port', 8000)
            }
        }
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Fallback configuration when core config is not available"""
        return {
            "app": {
                "title": "Kairos: The Context Keeper",
                "description": "Autonomous development supervisor powered by context engineering",
                "version": "1.0.0",
                "debug": False,
                "cors_origins": ["*"]
            },
            "database": {
                "url": "sqlite:///kairos_fallback.db",
                "pool_size": 5
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000
            }
        }
    
    def _create_fastapi_app(self):
        """Create FastAPI application with optimized settings"""
        self.app = FastAPI(
            title=self.config["app"]["title"],
            description=self.config["app"]["description"],
            version=self.config["app"]["version"],
            debug=self.config["app"]["debug"]
        )
        logger.info("✅ FastAPI application created")
    
    def _setup_middleware(self):
        """Setup middleware components with error handling"""
        # CORS middleware (always available)
        self._add_cors_middleware()
        
        # Optional middleware components
        self._try_add_rbac_middleware()
        self._try_add_rate_limiting_middleware()
        self._try_add_audit_logging()
    
    def _add_cors_middleware(self):
        """Add CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config["app"]["cors_origins"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("✅ CORS middleware added")
    
    def _try_add_rbac_middleware(self):
        """Try to add RBAC middleware if available"""
        try:
            from src.api.rbac_middleware import RBACMiddleware
            self.app.add_middleware(RBACMiddleware)
            self.middleware_components["rbac"] = True
            logger.info("✅ RBAC middleware added")
        except ImportError:
            logger.info("ℹ️ RBAC middleware not available")
            self.middleware_components["rbac"] = False
    
    def _try_add_rate_limiting_middleware(self):
        """Try to add rate limiting middleware if available"""
        try:
            from src.api.rate_limiting import RateLimiterMiddleware
            self.app.add_middleware(RateLimiterMiddleware)
            self.middleware_components["rate_limiting"] = True
            logger.info("✅ Rate limiting middleware added")
        except ImportError:
            logger.info("ℹ️ Rate limiting middleware not available")
            self.middleware_components["rate_limiting"] = False
    
    def _try_add_audit_logging(self):
        """Try to configure audit logging if available"""
        try:
            from src.api.audit_logging import configure_audit_logging
            configure_audit_logging()
            self.middleware_components["audit_logging"] = True
            logger.info("✅ Audit logging configured")
        except ImportError:
            logger.info("ℹ️ Audit logging not available")
            self.middleware_components["audit_logging"] = False
    
    def _setup_routes(self):
        """Setup application routes with error handling"""
        # Core routes (always available)
        self._add_core_routes()
        
        # Optional route groups
        self._try_add_auth_routes()
        self._try_add_admin_routes()
        self._try_add_supervisor_routes()
        self._try_add_memory_routes()
        self._try_add_websocket_routes()
    
    def _add_core_routes(self):
        """Add core application routes"""
        
        @self.app.get("/status")
        async def get_status():
            return self._build_status_response()
        
        @self.app.get("/health")
        async def health_check():
            return self._build_health_response()
        
        @self.app.get("/config")
        async def get_config_info():
            return self._build_config_response()
        
        logger.info("✅ Core routes added")
    
    def _try_add_auth_routes(self):
        """Try to add authentication routes if available"""
        try:
            from api.auth_routes import router as auth_router
            self.app.include_router(auth_router)
            logger.info("✅ Authentication routes added")
        except ImportError:
            logger.info("ℹ️ Authentication routes not available")
    
    def _try_add_admin_routes(self):
        """Try to add admin routes if available"""
        try:
            from api.admin_routes import router as admin_router
            self.app.include_router(admin_router)
            logger.info("✅ Admin routes added")
        except ImportError:
            logger.info("ℹ️ Admin routes not available")
    
    def _try_add_supervisor_routes(self):
        """Try to add supervisor routes if available"""
        try:
            from api.supervisor_routes import supervisor_router
            self.app.include_router(supervisor_router)
            logger.info("✅ Supervisor routes added")
        except ImportError:
            logger.info("ℹ️ Supervisor routes not available")
    
    def _try_add_memory_routes(self):
        """Add memory management routes"""
        
        @self.app.get("/api/memory/stats")
        async def get_memory_stats():
            return self._get_memory_statistics()
        
        @self.app.get("/api/memory/query")
        async def memory_query(query: str = "*"):
            return self._execute_memory_query(query)
        
        logger.info("✅ Memory routes added")
    
    def _try_add_websocket_routes(self):
        """Try to add WebSocket routes if available"""
        try:
            from api.websocket_endpoints import setup_websocket_routes
            setup_websocket_routes(self.app)
            logger.info("✅ WebSocket routes added")
        except ImportError:
            logger.info("ℹ️ WebSocket endpoints not available")
    
    def _setup_startup_events(self):
        """Setup application startup events"""
        
        @self.app.on_event("startup")
        async def startup_event():
            await self._execute_startup_sequence()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self._execute_shutdown_sequence()
    
    async def _execute_startup_sequence(self):
        """Execute optimized startup sequence with proper error handling"""
        startup_tasks = [
            ("Database Connection", self._initialize_database),
            ("Memory Systems", self._initialize_memory_systems),
            ("Agent Coordinator", self._initialize_agent_coordinator),
            ("Supervisor Agent", self._initialize_supervisor_agent),
            ("Background Tasks", self._start_background_tasks)
        ]
        
        logger.info("🚀 Starting Kairos initialization sequence...")
        
        for task_name, task_func in startup_tasks:
            try:
                logger.info(f"🔄 Initializing {task_name}...")
                await task_func()
                self.initialized_services[task_name.lower().replace(" ", "_")] = True
                logger.info(f"✅ {task_name} initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {task_name}: {e}")
                self.initialized_services[task_name.lower().replace(" ", "_")] = False
                # Continue with other services
        
        logger.info("🎯 Kairos initialization sequence completed")
    
    async def _initialize_database(self):
        """Initialize database connections with optimized pool settings"""
        try:
            import asyncpg
            from api.dependencies import init_dependencies
            
            # Create optimized connection pool
            db_pool = await asyncpg.create_pool(
                self.config["database"]["url"],
                min_size=2,  # Reduced minimum
                max_size=self.config["database"]["pool_size"],
                command_timeout=30,  # 30 second timeout
                server_settings={
                    'application_name': 'kairos_context_keeper',
                    'tcp_keepalives_idle': '600',
                    'tcp_keepalives_interval': '30',
                    'tcp_keepalives_count': '3',
                }
            )
            
            # Initialize dependencies
            await init_dependencies(db_pool)
            
            # Store pool for cleanup
            self.initialized_services["db_pool"] = db_pool
            
        except ImportError:
            logger.warning("Database dependencies not available, using fallback")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _initialize_memory_systems(self):
        """Initialize memory management systems"""
        try:
            from src.memory.memory_manager import MemoryManager
            
            # Initialize with optimized configuration
            memory_config = {
                "use_neo4j": False,  # Start with local for better reliability
                "use_qdrant": False,
                "persistence_path": "data/memory",
                "cache_ttl": 60,  # 1 minute cache
                "batch_size": 20   # Optimized batch size
            }
            
            memory_manager = MemoryManager(memory_config)
            self.initialized_services["memory_manager"] = memory_manager
            
        except ImportError:
            logger.warning("Memory manager not available")
        except Exception as e:
            logger.error(f"Memory systems initialization failed: {e}")
            raise
    
    async def _initialize_agent_coordinator(self):
        """Initialize the optimized agent coordinator"""
        try:
            from src.orchestration.agent_coordinator_optimized import OptimizedAgentCoordinator
            
            coordinator = OptimizedAgentCoordinator()
            
            # Register basic agents if available
            await self._register_available_agents(coordinator)
            
            self.initialized_services["agent_coordinator"] = coordinator
            
        except ImportError:
            logger.warning("Agent coordinator not available")
        except Exception as e:
            logger.error(f"Agent coordinator initialization failed: {e}")
            raise
    
    async def _register_available_agents(self, coordinator):
        """Register available agents with the coordinator"""
        agent_types = [
            ("ExecutionAgent", "src.agents.execution_agent", "ExecutionAgent"),
            ("RetrievalAgent", "src.agents.retrieval_agent", "RetrievalAgent"),
            ("GuardianAgent", "src.agents.guardian_agent", "GuardianAgent"),
            ("LinkAgent", "src.agents.link_agent", "LinkAgent"),
            ("ResearchAgent", "src.agents.research_agent", "ResearchAgent")
        ]
        
        for agent_name, module_path, class_name in agent_types:
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                agent_instance = agent_class()
                
                # Initialize agent if it has an initialize method
                if hasattr(agent_instance, 'initialize'):
                    await agent_instance.initialize()
                
                coordinator.register_agent(agent_name, agent_instance)
                logger.info(f"✅ Registered {agent_name}")
                
            except Exception as e:
                logger.warning(f"Failed to register {agent_name}: {e}")
    
    async def _initialize_supervisor_agent(self):
        """Initialize supervisor agent with optimized settings"""
        try:
            from src.agents.enhanced_supervisor import EnhancedSupervisorAgent
            
            supervisor_agent = EnhancedSupervisorAgent()
            await supervisor_agent.initialize()
            
            self.initialized_services["supervisor_agent"] = supervisor_agent
            
        except ImportError:
            logger.warning("Supervisor agent not available")
        except Exception as e:
            logger.error(f"Supervisor agent initialization failed: {e}")
            # Not critical, continue
    
    async def _start_background_tasks(self):
        """Start background maintenance tasks"""
        try:
            # Start cleanup task
            asyncio.create_task(self._periodic_cleanup())
            
            # Start health monitoring
            asyncio.create_task(self._periodic_health_check())
            
            # Start performance monitoring
            asyncio.create_task(self._periodic_performance_monitoring())
            
        except Exception as e:
            logger.error(f"Background tasks startup failed: {e}")
    
    async def _execute_shutdown_sequence(self):
        """Execute graceful shutdown sequence"""
        logger.info("🔄 Starting graceful shutdown...")
        
        shutdown_tasks = [
            ("Background Tasks", self._stop_background_tasks),
            ("Agent Coordinator", self._shutdown_agent_coordinator),
            ("Memory Systems", self._shutdown_memory_systems),
            ("Database", self._shutdown_database)
        ]
        
        for task_name, task_func in shutdown_tasks:
            try:
                logger.info(f"🔄 Shutting down {task_name}...")
                await task_func()
                logger.info(f"✅ {task_name} shutdown completed")
            except Exception as e:
                logger.error(f"❌ Error shutting down {task_name}: {e}")
        
        logger.info("🎯 Graceful shutdown completed")
    
    # === UTILITY METHODS ===
    
    def _build_status_response(self) -> Dict[str, Any]:
        """Build comprehensive status response"""
        return {
            "daemon": "running",
            "context_engine": "active",
            "initialized_services": self.initialized_services,
            "middleware_status": self.middleware_components,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": self._calculate_uptime()
        }
    
    def _build_health_response(self) -> Dict[str, Any]:
        """Build health check response"""
        healthy_services = sum(1 for status in self.initialized_services.values() if status)
        total_services = len(self.initialized_services)
        
        health_status = "healthy" if healthy_services == total_services else "degraded"
        
        return {
            "status": health_status,
            "services": {
                "healthy": healthy_services,
                "total": total_services,
                "details": self.initialized_services
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _build_config_response(self) -> Dict[str, Any]:
        """Build configuration info response (safe subset)"""
        return {
            "app": {
                "title": self.config["app"]["title"],
                "version": self.config["app"]["version"],
                "debug": self.config["app"]["debug"]
            },
            "features": {
                "middleware": self.middleware_components,
                "services": list(self.initialized_services.keys())
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        if "memory_manager" in self.initialized_services:
            try:
                memory_manager = self.initialized_services["memory_manager"]
                return memory_manager.get_performance_stats()
            except Exception as e:
                logger.error(f"Failed to get memory stats: {e}")
        
        return {
            "status": "memory_manager_not_available",
            "timestamp": datetime.now().isoformat()
        }
    
    def _execute_memory_query(self, query: str) -> Dict[str, Any]:
        """Execute memory query with fallback"""
        # Simplified memory query for demo
        nodes = [
            {"id": "kairos", "label": "Kairos System", "type": "system"},
            {"id": "agents", "label": "AI Agents", "type": "agents"},
            {"id": "memory", "label": "Memory Engine", "type": "memory"}
        ]
        
        relationships = [
            {"from": "kairos", "to": "agents", "type": "manages"},
            {"from": "agents", "to": "memory", "type": "uses"}
        ]
        
        return {
            "query": query,
            "nodes": nodes,
            "relationships": relationships,
            "count": len(nodes),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_uptime(self) -> float:
        """Calculate application uptime in seconds"""
        if not hasattr(self, '_start_time'):
            self._start_time = datetime.now()
        
        return (datetime.now() - self._start_time).total_seconds()
    
    # === BACKGROUND TASK METHODS ===
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up completed tasks if coordinator available
                if "agent_coordinator" in self.initialized_services:
                    coordinator = self.initialized_services["agent_coordinator"]
                    await coordinator.cleanup_completed_tasks(older_than_hours=24)
                
                # Clean up memory cache if available
                if "memory_manager" in self.initialized_services:
                    memory_manager = self.initialized_services["memory_manager"]
                    memory_manager.clear_cache()
                
                logger.info("🧹 Periodic cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
    
    async def _periodic_health_check(self):
        """Periodic health check of agents"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                if "agent_coordinator" in self.initialized_services:
                    coordinator = self.initialized_services["agent_coordinator"]
                    
                    # Check health of all registered agents
                    for agent_type in coordinator.get_registered_agents():
                        health_status = await coordinator.check_agent_health(agent_type)
                        if health_status.get("status") != "healthy":
                            logger.warning(f"Agent {agent_type} health check failed: {health_status}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _periodic_performance_monitoring(self):
        """Periodic performance monitoring"""
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                
                if "agent_coordinator" in self.initialized_services:
                    coordinator = self.initialized_services["agent_coordinator"]
                    perf_stats = coordinator.get_performance_stats()
                    
                    success_rate = perf_stats.get("success_rate_percent", 0)
                    if success_rate < 80:  # Alert if success rate drops below 80%
                        logger.warning(f"⚠️ System performance degraded: {success_rate}% success rate")
                    
                    logger.info(f"📊 System performance: {success_rate}% success rate, "
                              f"{perf_stats['task_queues']['pending']} tasks pending")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    # === SHUTDOWN METHODS ===
    
    async def _stop_background_tasks(self):
        """Stop background tasks"""
        # Background tasks will stop automatically when main loop stops
        pass
    
    async def _shutdown_agent_coordinator(self):
        """Shutdown agent coordinator"""
        if "agent_coordinator" in self.initialized_services:
            coordinator = self.initialized_services["agent_coordinator"]
            # Perform any necessary cleanup
            # coordinator.shutdown() if such method exists
    
    async def _shutdown_memory_systems(self):
        """Shutdown memory systems"""
        if "memory_manager" in self.initialized_services:
            memory_manager = self.initialized_services["memory_manager"]
            memory_manager.close()
    
    async def _shutdown_database(self):
        """Shutdown database connections"""
        if "db_pool" in self.initialized_services:
            db_pool = self.initialized_services["db_pool"]
            await db_pool.close()


# Factory function for creating the application
def create_optimized_kairos_app() -> FastAPI:
    """Create optimized Kairos application"""
    builder = KairosApplicationBuilder()
    return builder.build_application()


# Main execution
if __name__ == "__main__":
    app = create_optimized_kairos_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
