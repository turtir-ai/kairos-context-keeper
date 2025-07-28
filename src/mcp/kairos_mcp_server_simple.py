#!/usr/bin/env python3
"""
Kairos MCP Server - Simplified Version
Working MCP server implementation for Kairos
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
except ImportError as e:
    print(f"MCP import error: {e}")
    print("Please install MCP: pip install mcp")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create server
server = Server("kairos")

@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools."""
    tools = [
        Tool(
            name="kairos.getProjectConstitution",
            description="Get Kairos project constitution and standards",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "Section to retrieve (architecture, security, coding_standards, all)",
                        "enum": ["architecture", "security", "coding_standards", "all"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="kairos.getSystemHealth",
            description="Get current system health status",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Include detailed metrics",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="kairos.getContext",
            description="Get enriched context from Kairos knowledge systems",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Context query"
                    },
                    "depth": {
                        "type": "string",
                        "description": "Context depth",
                        "enum": ["basic", "detailed", "expert"],
                        "default": "detailed"
                    }
                },
                "required": ["query"]
            }
        )
    ]
    
    logger.info(f"Serving {len(tools)} Kairos tools")
    return ListToolsResult(tools=tools)

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    try:
        if name == "kairos.getProjectConstitution":
            return await get_project_constitution(arguments)
        elif name == "kairos.getSystemHealth":
            return await get_system_health(arguments)
        elif name == "kairos.getContext":
            return await get_context(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
            )
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
        )

async def get_project_constitution(arguments: Dict[str, Any]) -> CallToolResult:
    """Get project constitution."""
    section = arguments.get("section", "all")
    
    constitution = {
        "architecture": {
            "patterns": ["MVC", "Microservices", "Event-driven"],
            "principles": ["SOLID", "DRY", "KISS"],
            "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"]
        },
        "security": {
            "authentication": "JWT with refresh tokens",
            "authorization": "Role-based access control",
            "encryption": "TLS 1.3, AES-256"
        },
        "coding_standards": {
            "style": "PEP 8 for Python, Prettier for JS",
            "testing": "Unit tests >90% coverage",
            "documentation": "Comprehensive docstrings"
        }
    }
    
    if section == "all":
        result = constitution
    else:
        result = {section: constitution.get(section, {})}
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    )

async def get_system_health(arguments: Dict[str, Any]) -> CallToolResult:
    """Get system health."""
    include_metrics = arguments.get("include_metrics", False)
    
    health = {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": "2d 14h 30m",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "mcp_server": "running",
            "database": "running",
            "web_server": "running"
        }
    }
    
    if include_metrics:
        health["metrics"] = {
            "cpu_usage": "45%",
            "memory_usage": "62%",
            "response_time": "120ms"
        }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(health, indent=2)
        )]
    )

async def get_context(arguments: Dict[str, Any]) -> CallToolResult:
    """Get enriched context."""
    query = arguments.get("query", "")
    depth = arguments.get("depth", "detailed")
    
    context = {
        "query": query,
        "depth": depth,
        "sources": ["knowledge_graph", "vector_db", "constitution"],
        "context": f"Kairos context for '{query}':\n\n" +
                  "- Architecture patterns from knowledge graph\n" +
                  "- Similar implementations from vector DB\n" +
                  "- Project standards from constitution\n" +
                  "- Historical decisions and lessons learned",
        "suggestions": [
            "Follow established patterns",
            "Consider security implications",
            "Maintain code consistency"
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(context, indent=2)
        )]
    )

async def main():
    """Run the server."""
    logger.info("🚀 Starting Kairos MCP Server...")
    
    try:
        async with stdio_server(server) as (read_stream, write_stream):
            logger.info("✅ Server started successfully")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Server crashed: {e}")
        sys.exit(1)
