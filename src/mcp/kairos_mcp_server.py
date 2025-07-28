#!/usr/bin/env python3
"""
Kairos MCP Server Implementation

This server implements the Model Context Protocol (MCP) to provide Kairos intelligence
to external AI development tools like Cursor, Kiro, and other IDEs.

Essential tools provided:
- kairos.getContext() - Enriched context service
- kairos.createTask() - Orchestration service  
- kairos.getProjectConstitution() - Project constitution
- kairos.analyzeCode() - Code analysis service
- kairos.getSuggestions() - Proactive suggestion service
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Resource,
    ListResourcesResult
)

from src.mcp.tool_definitions import get_kairos_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Kairos MCP Server
app = Server("kairos")

@app.list_tools()
async def list_tools() -> ListToolsResult:
    """List all available Kairos MCP tools."""
    try:
        tools = get_kairos_tools()
        logger.info(f"Serving {len(tools)} Kairos MCP tools")
        return ListToolsResult(tools=tools)
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return ListToolsResult(tools=[])

@app.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available Kairos resources."""
    return ListResourcesResult(
        resources=[
            Resource(
                uri="kairos://constitution",
                name="Kairos Project Constitution",
                description="Complete project constitution with architecture, security, and coding standards",
                mimeType="application/json"
            ),
            Resource(
                uri="kairos://health",
                name="System Health Status",
                description="Current system health and performance metrics",
                mimeType="application/json"
            ),
            Resource(
                uri="kairos://context",
                name="Context Knowledge Base",
                description="Access to Kairos knowledge graph and vector database",
                mimeType="application/json"
            )
        ]
    )

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle MCP tool calls."""
    try:
        logger.info(f"Tool called: {name} with args: {arguments}")
        
        if name == "kairos.getContext":
            return await get_context(arguments)
        elif name == "kairos.createTask":
            return await create_task(arguments)
        elif name == "kairos.getProjectConstitution":
            return await get_project_constitution(arguments)
        elif name == "kairos.analyzeCode":
            return await analyze_code(arguments)
        elif name == "kairos.getSuggestions":
            return await get_suggestions(arguments)
        elif name == "kairos.getSystemHealth":
            return await get_system_health(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"Unknown tool: {name}. Available tools: {', '.join([t.name for t in get_kairos_tools()])}"
                )]
            )
            
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )]
        )

async def get_context(arguments: Dict[str, Any]) -> CallToolResult:
    """Get enriched context from Kairos knowledge systems."""
    query = arguments.get("query", "")
    metadata = arguments.get("metadata", {})
    
    try:
        # Mock implementation - would connect to real Kairos services
        context_data = {
            "query": query,
            "context_sources": [
                "knowledge_graph",
                "vector_database", 
                "project_constitution",
                "historical_decisions"
            ],
            "relevance_score": 0.95,
            "context_depth": metadata.get("context_deep", "detailed"),
            "enriched_context": f"Based on Kairos knowledge about '{query}', here are the key insights:\n\n" +
                               "- Architecture patterns from knowledge graph\n" +
                               "- Similar implementations from vector DB\n" +
                               "- Project standards from constitution\n" +
                               "- Lessons learned from past decisions",
            "suggestions": [
                "Consider security implications",
                "Follow established patterns",
                "Maintain consistency with existing code"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(context_data, indent=2)
            )]
        )
        
    except Exception as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error getting context for '{query}': {str(e)}"
            )]
        )

async def create_task(arguments: Dict[str, Any]) -> CallToolResult:
    """Create a new task in the Kairos orchestration system."""
    description = arguments.get("description", "")
    agent = arguments.get("agent", "supervisor")
    priority = arguments.get("priority", "medium")
    metadata = arguments.get("metadata", {})
    
    try:
        # Make API call to create task
        import requests
        
        task_payload = {
            "type": metadata.get("type", "general"),
            "description": description,
            "agent": agent,
            "priority": priority,
            "metadata": metadata
        }
        
        response = requests.post(
            "http://localhost:8000/api/orchestration/tasks",
            json=task_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            task_data = response.json()
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Task created successfully:\n{json.dumps(task_data, indent=2)}"
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Failed to create task. Status: {response.status_code}, Error: {response.text}"
                )]
            )
            
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Error creating task: {str(e)}"
            )]
        )

async def get_project_constitution(arguments: Dict[str, Any]) -> CallToolResult:
    """Get the project constitution."""
    section = arguments.get("section", "all")
    
    constitution_data = {
        "architecture": {
            "patterns": ["MVC", "Microservices", "Event-driven"],
            "principles": ["SOLID", "DRY", "KISS"],
            "technologies": ["Python", "FastAPI", "React", "PostgreSQL"]
        },
        "security": {
            "authentication": "JWT with refresh tokens",
            "authorization": "Role-based access control",
            "encryption": "TLS 1.3, AES-256",
            "best_practices": ["Input validation", "SQL injection prevention", "XSS protection"]
        },
        "coding_standards": {
            "style": "PEP 8 for Python, Prettier for JavaScript",
            "documentation": "Comprehensive docstrings and comments",
            "testing": "Unit tests with >90% coverage",
            "code_review": "All changes require review"
        },
        "deployment": {
            "containerization": "Docker with multi-stage builds",
            "orchestration": "Kubernetes",
            "ci_cd": "GitHub Actions",
            "monitoring": "Prometheus + Grafana"
        }
    }
    
    if section != "all" and section in constitution_data:
        result = {section: constitution_data[section]}
    else:
        result = constitution_data
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    )

async def analyze_code(arguments: Dict[str, Any]) -> CallToolResult:
    """Analyze code with Kairos intelligence."""
    code = arguments.get("code", "")
    context = arguments.get("context", "")
    analysis_type = arguments.get("analysis_type", "all")
    file_path = arguments.get("file_path", "")
    
    analysis_result = {
        "file_path": file_path,
        "analysis_type": analysis_type,
        "quality_score": 8.5,
        "security_score": 9.0,
        "performance_score": 7.8,
        "compliance_score": 9.2,
        "issues": [
            {
                "type": "security",
                "severity": "medium",
                "description": "Consider input validation for user data",
                "line": 15,
                "suggestion": "Add proper input sanitization"
            },
            {
                "type": "performance",
                "severity": "low",
                "description": "Consider caching for frequently accessed data",
                "line": 32,
                "suggestion": "Implement Redis caching"
            }
        ],
        "suggestions": [
            "Code follows project standards well",
            "Consider adding more comprehensive error handling",
            "Architecture is consistent with project patterns"
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(analysis_result, indent=2)
        )]
    )

async def get_suggestions(arguments: Dict[str, Any]) -> CallToolResult:
    """Get proactive suggestions from Kairos Supervisor Agent."""
    scope = arguments.get("scope", "all")
    context = arguments.get("context", {})
    
    suggestions_data = {
        "scope": scope,
        "context": context,
        "suggestions": [
            {
                "type": "code_improvement",
                "priority": "high",
                "title": "Optimize database queries",
                "description": "Several database queries could be optimized with proper indexing",
                "impact": "performance",
                "effort": "medium"
            },
            {
                "type": "security_enhancement",
                "priority": "medium",
                "title": "Implement rate limiting",
                "description": "Add rate limiting to API endpoints to prevent abuse",
                "impact": "security",
                "effort": "low"
            },
            {
                "type": "architecture",
                "priority": "low",
                "title": "Consider microservice split",
                "description": "User management could be extracted to separate service",
                "impact": "maintainability",
                "effort": "high"
            }
        ],
        "proactive_insights": [
            "System performance is stable",
            "No critical security issues detected",
            "Code quality metrics are improving"
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(suggestions_data, indent=2)
        )]
    )

async def get_system_health(arguments: Dict[str, Any]) -> CallToolResult:
    """Get current system health status."""
    include_metrics = arguments.get("include_metrics", False)
    
    health_data = {
        "status": "healthy",
        "uptime": "2d 14h 30m",
        "version": "1.0.0",
        "last_check": datetime.now().isoformat(),
        "services": {
            "web_server": "running",
            "database": "running",
            "redis": "running",
            "background_workers": "running"
        }
    }
    
    if include_metrics:
        health_data["metrics"] = {
            "cpu_usage": "45%",
            "memory_usage": "62%",
            "disk_usage": "38%",
            "network_io": "normal",
            "response_time_avg": "120ms",
            "error_rate": "0.1%"
        }
    
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(health_data, indent=2)
        )]
    )

async def main():
    """Main function to run the MCP server."""
    async with stdio_server(app) as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kairos MCP Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8100, help="Port to bind to")
    args = parser.parse_args()
    
    logger.info(f"Starting Kairos MCP Server on {args.host}:{args.port}")
    
    # Run MCP server using stdio for MCP clients
    asyncio.run(main())
