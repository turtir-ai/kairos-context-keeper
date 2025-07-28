"""
Plugin Management API
Provides endpoints for managing and interacting with the plugin system
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime

router = APIRouter()

@router.get("/plugins")
async def list_plugins():
    """List all available plugins"""
    try:
        # Import agent coordinator to access plugin loader
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Get loaded plugins
        loaded_plugins = plugin_loader.list_loaded_plugins()
        
        # Get capabilities for each plugin
        plugins_info = []
        for plugin_name in loaded_plugins:
            plugin_instance = plugin_loader.get_plugin(plugin_name)
            if plugin_instance:
                metadata = plugin_instance.get_metadata()
                health = await plugin_instance.health_check()
                
                plugins_info.append({
                    "name": plugin_name,
                    "version": metadata.version,
                    "author": metadata.author,
                    "description": metadata.description,
                    "capabilities": [
                        {
                            "name": cap.name,
                            "description": cap.description,
                            "parameters": cap.parameters,
                            "required_permissions": cap.required_permissions or []
                        }
                        for cap in metadata.capabilities
                    ],
                    "dependencies": metadata.dependencies or [],
                    "health": health,
                    "loaded": True
                })
        
        return {
            "plugins": plugins_info,
            "total_plugins": len(plugins_info),
            "loaded_plugins": len(loaded_plugins),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plugins: {str(e)}")

@router.get("/plugins/{plugin_name}")
async def get_plugin_details(plugin_name: str):
    """Get detailed information about a specific plugin"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        plugin_instance = plugin_loader.get_plugin(plugin_name)
        
        if not plugin_instance:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        
        metadata = plugin_instance.get_metadata()
        health = await plugin_instance.health_check()
        
        return {
            "name": plugin_name,
            "metadata": {
                "version": metadata.version,
                "author": metadata.author,
                "description": metadata.description,
                "dependencies": metadata.dependencies or [],
                "config_schema": metadata.config_schema or {}
            },
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "parameters": cap.parameters,
                    "required_permissions": cap.required_permissions or []
                }
                for cap in metadata.capabilities
            ],
            "health": health,
            "config": plugin_instance.config,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get plugin details: {str(e)}")

@router.post("/plugins/{plugin_name}/execute")
async def execute_plugin_task(plugin_name: str, task: Dict[str, Any]):
    """Execute a task using a specific plugin"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Validate task format
        if "action" not in task:
            raise HTTPException(status_code=400, detail="Task must include 'action' field")
        
        # Execute task through plugin loader
        result = await plugin_loader.execute_plugin_task(plugin_name, task)
        
        return {
            "plugin_name": plugin_name,
            "task": task,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute plugin task: {str(e)}")

@router.post("/plugins/{plugin_name}/reload")
async def reload_plugin(plugin_name: str):
    """Reload a specific plugin"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Reload the plugin
        success = await plugin_loader.reload_plugin(plugin_name)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to reload plugin '{plugin_name}'")
        
        return {
            "plugin_name": plugin_name,
            "action": "reloaded",
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload plugin: {str(e)}")

@router.post("/plugins/{plugin_name}/unload")
async def unload_plugin(plugin_name: str):
    """Unload a specific plugin"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Unload the plugin
        success = await plugin_loader.unload_plugin(plugin_name)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to unload plugin '{plugin_name}'")
        
        return {
            "plugin_name": plugin_name,
            "action": "unloaded",
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unload plugin: {str(e)}")

@router.post("/plugins/discover")
async def discover_plugins():
    """Discover available plugins in the plugin directory"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Discover plugins
        discovered = await plugin_loader.discover_plugins()
        
        return {
            "action": "discovery",
            "discovered_plugins": discovered,
            "total_discovered": len(discovered),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover plugins: {str(e)}")

@router.post("/plugins/{plugin_name}/load")
async def load_plugin(plugin_name: str, config: Optional[Dict[str, Any]] = None):
    """Load a specific plugin with optional configuration"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Load the plugin
        success = await plugin_loader.load_plugin(plugin_name, config)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to load plugin '{plugin_name}'")
        
        # Register plugin as agent if successful
        plugin_instance = plugin_loader.get_plugin(plugin_name)
        if plugin_instance:
            metadata = plugin_instance.get_metadata()
            capabilities = [cap.name for cap in metadata.capabilities]
            agent_coordinator.register_agent(f"{plugin_name}_plugin", plugin_instance, capabilities)
        
        return {
            "plugin_name": plugin_name,
            "action": "loaded",
            "success": True,
            "config": config,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load plugin: {str(e)}")

@router.get("/plugins/capabilities")
async def get_all_capabilities():
    """Get all capabilities from all loaded plugins"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Get all capabilities
        capabilities = plugin_loader.get_all_capabilities()
        
        return {
            "capabilities": capabilities,
            "total_plugins": len(capabilities),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")

@router.post("/plugins/find-for-task")
async def find_plugin_for_task(task: Dict[str, Any]):
    """Find a suitable plugin for a given task"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        
        # Find suitable plugin
        plugin_name = await plugin_loader.find_plugin_for_task(task)
        
        if not plugin_name:
            return {
                "task": task,
                "suitable_plugin": None,
                "message": "No suitable plugin found for this task",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "task": task,
            "suitable_plugin": plugin_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find plugin for task: {str(e)}")

@router.get("/plugins/health")
async def check_all_plugins_health():
    """Check health status of all loaded plugins"""
    try:
        try:
            from ..orchestration.agent_coordinator import agent_coordinator
        except ImportError:
            from orchestration.agent_coordinator import agent_coordinator
        
        plugin_loader = agent_coordinator.plugin_loader
        loaded_plugins = plugin_loader.list_loaded_plugins()
        
        health_reports = {}
        for plugin_name in loaded_plugins:
            plugin_instance = plugin_loader.get_plugin(plugin_name)
            if plugin_instance:
                health_reports[plugin_name] = await plugin_instance.health_check()
        
        # Calculate overall health
        healthy_count = sum(1 for health in health_reports.values() if health.get("healthy", False))
        overall_health = "healthy" if healthy_count == len(health_reports) else "degraded" if healthy_count > 0 else "unhealthy"
        
        return {
            "overall_health": overall_health,
            "total_plugins": len(health_reports),
            "healthy_plugins": healthy_count,
            "plugin_health": health_reports,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check plugin health: {str(e)}")
