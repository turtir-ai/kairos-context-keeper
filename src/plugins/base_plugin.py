"""
Base Plugin Interface for Kairos Plugin System
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class PluginCapability:
    """Describes a capability provided by a plugin"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = None

@dataclass
class PluginMetadata:
    """Plugin metadata information"""
    name: str
    version: str
    author: str
    description: str
    capabilities: List[PluginCapability]
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None

class BasePlugin(ABC):
    """Abstract base class for all Kairos plugins"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"plugin.{self.get_metadata().name}")
        self._initialized = False
        
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata including name, version, and capabilities"""
        pass
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the plugin with necessary resources
        Returns True if initialization successful
        """
        pass
        
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using this plugin
        
        Args:
            task: Dictionary containing:
                - action: The specific action to perform
                - parameters: Parameters for the action
                - context: Additional context information
                
        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - result: The result of the execution
                - error: Error message if any
        """
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources when plugin is being unloaded"""
        pass
        
    def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate that a task can be handled by this plugin"""
        if not task.get('action'):
            return False
            
        # Check if action is in plugin capabilities
        capabilities = self.get_metadata().capabilities
        valid_actions = [cap.name for cap in capabilities]
        
        return task['action'] in valid_actions
        
    def get_capability(self, action: str) -> Optional[PluginCapability]:
        """Get capability details for a specific action"""
        for cap in self.get_metadata().capabilities:
            if cap.name == action:
                return cap
        return None
        
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the plugin
        
        Returns:
            Dictionary with health status information
        """
        return {
            "healthy": self._initialized,
            "name": self.get_metadata().name,
            "version": self.get_metadata().version
        }
        
    def __repr__(self):
        metadata = self.get_metadata()
        return f"<Plugin: {metadata.name} v{metadata.version}>"
