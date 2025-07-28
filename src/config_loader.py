"""
Configuration Loader for Kairos
Handles loading and managing configuration from kairos.toml
"""

import os
import toml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import threading

@dataclass
class ConfigSchema:
    """Configuration schema with defaults"""
    general: Dict[str, Any] = field(default_factory=lambda: {
        "name": "Kairos Context Keeper",
        "version": "0.5.0",
        "environment": "development",
        "log_level": "INFO"
    })
    daemon: Dict[str, Any] = field(default_factory=lambda: {
        "host": "0.0.0.0",
        "port": 8000,
        "workers": 4,
        "max_concurrent_tasks": 10,
        "task_timeout": 300,
        "heartbeat_interval": 30
    })
    llm: Dict[str, Any] = field(default_factory=dict)
    database: Dict[str, Any] = field(default_factory=dict)
    cache: Dict[str, Any] = field(default_factory=dict)
    monitoring: Dict[str, Any] = field(default_factory=dict)
    security: Dict[str, Any] = field(default_factory=dict)
    plugins: Dict[str, Any] = field(default_factory=dict)
    fine_tuning: Dict[str, Any] = field(default_factory=dict)
    multi_tenancy: Dict[str, Any] = field(default_factory=dict)
    kubernetes: Dict[str, Any] = field(default_factory=dict)
    observability: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, Any] = field(default_factory=dict)
    api: Dict[str, Any] = field(default_factory=dict)
    email: Dict[str, Any] = field(default_factory=dict)

class ConfigLoader:
    """Singleton configuration loader"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = logging.getLogger(__name__)
            self.config_path = None
            self.config: ConfigSchema = ConfigSchema()
            self._raw_config: Dict[str, Any] = {}
            self._watchers: Dict[str, list] = {}
            self.initialized = True
    
    def load(self, config_path: Optional[str] = None) -> bool:
        """Load configuration from TOML file"""
        # Find config file
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Search for kairos.toml in common locations
            search_paths = [
                Path.cwd() / "kairos.toml",
                Path.cwd().parent / "kairos.toml",
                Path.home() / ".kairos" / "kairos.toml",
                Path("/etc/kairos/kairos.toml")
            ]
            
            for path in search_paths:
                if path.exists():
                    self.config_path = path
                    break
            else:
                self.logger.warning("No configuration file found, using defaults")
                return True
        
        try:
            # Load TOML file
            with open(self.config_path, 'r') as f:
                self._raw_config = toml.load(f)
            
            # Replace environment variables
            self._substitute_env_vars(self._raw_config)
            
            # Update config schema
            for key, value in self._raw_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
            # Notify watchers
            self._notify_watchers()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> None:
        """Recursively substitute environment variables in config"""
        for key, value in config.items():
            if isinstance(value, dict):
                self._substitute_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env_value = os.environ.get(env_var)
                if env_value:
                    config[key] = env_value
                else:
                    self.logger.warning(f"Environment variable {env_var} not found")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path
        Example: config.get('llm.providers.ollama.base_url')
        """
        keys = key_path.split('.')
        value = self._raw_config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Set configuration value at runtime
        Note: This doesn't persist to file
        """
        keys = key_path.split('.')
        config = self._raw_config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
        
        # Update the config schema if applicable
        if hasattr(self.config, keys[0]):
            schema_attr = getattr(self.config, keys[0])
            if isinstance(schema_attr, dict):
                self._update_nested_dict(schema_attr, keys[1:], value)
        
        # Notify watchers
        self._notify_watchers(key_path)
        
        return True
    
    def _update_nested_dict(self, d: dict, keys: list, value: Any):
        """Update nested dictionary"""
        for key in keys[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value
    
    def watch(self, key_path: str, callback: callable) -> None:
        """Watch for configuration changes"""
        if key_path not in self._watchers:
            self._watchers[key_path] = []
        self._watchers[key_path].append(callback)
    
    def _notify_watchers(self, key_path: Optional[str] = None) -> None:
        """Notify watchers of configuration changes"""
        if key_path:
            # Notify specific watchers
            if key_path in self._watchers:
                for callback in self._watchers[key_path]:
                    try:
                        callback(self.get(key_path))
                    except Exception as e:
                        self.logger.error(f"Watcher callback failed: {e}")
            
            # Notify parent watchers
            parts = key_path.split('.')
            for i in range(len(parts)):
                parent_path = '.'.join(parts[:i])
                if parent_path in self._watchers:
                    for callback in self._watchers[parent_path]:
                        try:
                            callback(self.get(parent_path))
                        except Exception as e:
                            self.logger.error(f"Watcher callback failed: {e}")
        else:
            # Notify all watchers
            for callbacks in self._watchers.values():
                for callback in callbacks:
                    try:
                        callback(self._raw_config)
                    except Exception as e:
                        self.logger.error(f"Watcher callback failed: {e}")
    
    def reload(self) -> bool:
        """Reload configuration from file"""
        if self.config_path:
            return self.load(str(self.config_path))
        return False
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get feature flag value"""
        return self.get(f'features.{flag_name}', False)
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.get('general.environment') == 'production'
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self._raw_config.copy()

# Global config instance
config = ConfigLoader()
