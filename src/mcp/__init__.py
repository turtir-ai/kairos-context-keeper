"""
Model Context Protocol (MCP) Module for Kairos

This module provides enhanced context-aware communication between the system and LLMs.
"""

from .model_context_protocol import (
    ModelContextProtocol,
    MCPContext,
    MCPMessage,
    MCPTool,
    MCPMessageType,
    MCPRole,
    mcp
)

__all__ = [
    'ModelContextProtocol',
    'MCPContext',
    'MCPMessage',
    'MCPTool',
    'MCPMessageType',
    'MCPRole',
    'mcp'
]
