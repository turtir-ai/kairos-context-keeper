"""
Kairos Plugin System
====================

This module provides the plugin infrastructure for extending Kairos capabilities
without modifying the core codebase.
"""

from .base_plugin import BasePlugin
from .plugin_loader import PluginLoader

__all__ = ['BasePlugin', 'PluginLoader']
