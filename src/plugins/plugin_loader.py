"""
Dynamic Plugin Loader for Kairos
"""

import os
import sys
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Type, Optional
import asyncio

from .base_plugin import BasePlugin, PluginMetadata

class PluginLoader:
    """Dynamically loads and manages plugins"""
    
    def __init__(self, plugin_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.plugin_dir = Path(plugin_dir) if plugin_dir else Path(__file__).parent
        self.loaded_plugins: Dict[str, BasePlugin] = {}
        self.plugin_classes: Dict[str, Type[BasePlugin]] = {}
        
    async def discover_plugins(self) -> List[str]:
        """Discover all available plugins in the plugin directory"""
        discovered = []
        
        # Ensure plugin directory is in Python path
        if str(self.plugin_dir.parent) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir.parent))
            
        # Scan for Python files in plugin directory
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.stem.startswith("_") or file_path.stem in ["base_plugin", "plugin_loader"]:
                continue
                
            try:
                # Import the module
                module_name = f"plugins.{file_path.stem}"
                module = importlib.import_module(module_name)
                
                # Find all classes that inherit from BasePlugin
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BasePlugin) and 
                        obj != BasePlugin):
                        
                        # Get plugin metadata
                        try:
                            # Create temporary instance to get metadata
                            temp_instance = obj()
                            metadata = temp_instance.get_metadata()
                            plugin_name = metadata.name
                            
                            self.plugin_classes[plugin_name] = obj
                            discovered.append(plugin_name)
                            self.logger.info(f"Discovered plugin: {plugin_name} v{metadata.version}")
                            
                        except Exception as e:
                            self.logger.error(f"Failed to get metadata from {name}: {e}")
                            
            except Exception as e:
                self.logger.error(f"Failed to import {file_path.stem}: {e}")
                
        return discovered
        
    async def load_plugin(self, plugin_name: str, config: Dict = None) -> bool:
        """Load a specific plugin"""
        if plugin_name in self.loaded_plugins:
            self.logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
            
        if plugin_name not in self.plugin_classes:
            self.logger.error(f"Plugin {plugin_name} not found")
            return False
            
        try:
            # Create plugin instance
            plugin_class = self.plugin_classes[plugin_name]
            plugin_instance = plugin_class(config)
            
            # Initialize the plugin
            if await plugin_instance.initialize():
                self.loaded_plugins[plugin_name] = plugin_instance
                plugin_instance._initialized = True
                self.logger.info(f"Successfully loaded plugin: {plugin_name}")
                return True
            else:
                self.logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return False
            
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin"""
        if plugin_name not in self.loaded_plugins:
            self.logger.warning(f"Plugin {plugin_name} is not loaded")
            return False
            
        try:
            plugin = self.loaded_plugins[plugin_name]
            await plugin.cleanup()
            del self.loaded_plugins[plugin_name]
            self.logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
            
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin (unload and load again)"""
        config = None
        if plugin_name in self.loaded_plugins:
            config = self.loaded_plugins[plugin_name].config
            await self.unload_plugin(plugin_name)
            
        # Reimport the module
        if plugin_name in self.plugin_classes:
            del self.plugin_classes[plugin_name]
            
        await self.discover_plugins()
        return await self.load_plugin(plugin_name, config)
        
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin instance"""
        return self.loaded_plugins.get(plugin_name)
        
    def list_loaded_plugins(self) -> List[str]:
        """List all currently loaded plugins"""
        return list(self.loaded_plugins.keys())
        
    def get_all_capabilities(self) -> Dict[str, List[str]]:
        """Get all capabilities from loaded plugins"""
        capabilities = {}
        for name, plugin in self.loaded_plugins.items():
            metadata = plugin.get_metadata()
            capabilities[name] = [cap.name for cap in metadata.capabilities]
        return capabilities
        
    async def execute_plugin_task(self, plugin_name: str, task: Dict) -> Dict:
        """Execute a task on a specific plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {
                "success": False,
                "error": f"Plugin {plugin_name} not loaded"
            }
            
        if not plugin.validate_task(task):
            return {
                "success": False,
                "error": f"Invalid task for plugin {plugin_name}"
            }
            
        try:
            return await plugin.execute(task)
        except Exception as e:
            self.logger.error(f"Plugin execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def find_plugin_for_task(self, task: Dict) -> Optional[str]:
        """Find a suitable plugin for a given task"""
        action = task.get('action')
        if not action:
            return None
            
        for name, plugin in self.loaded_plugins.items():
            if plugin.validate_task(task):
                return name
                
        return None
        
    async def cleanup_all(self):
        """Cleanup all loaded plugins"""
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)
