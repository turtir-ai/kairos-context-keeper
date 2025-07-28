"""
Kairos MCP Tool Definitions

Essential MCP tools as defined in Sprint 8 plan:
- kairos.getContext(query: str, metadata: dict) - Enriched context service
- kairos.createTask(description: str, agent: str, priority: str) - Orchestration service
- kairos.getProjectConstitution() - Project constitution
- kairos.analyzeCode(code: str, context: str) - Code analysis service
- kairos.getSuggestions(scope: str) - Proactive suggestion service
"""

from mcp.types import Tool
from typing import Dict, Any, List

def get_kairos_tools() -> List[Tool]:
    """Get all Kairos MCP tools."""
    return [
        Tool(
            name="kairos.getContext",
            description="Get enriched context from Kairos knowledge graph, vector DB, and project constitution",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The context query or topic"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata for context refinement",
                        "properties": {
                            "file_path": {"type": "string"},
                            "function_name": {"type": "string"},
                            "context_depth": {"type": "string", "enum": ["basic", "detailed", "expert"]},
                            "relevance_scope": {"type": "string"}
                        }
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="kairos.createTask",
            description="Create a new task in Kairos orchestration system",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "agent": {
                        "type": "string",
                        "description": "Target agent for the task",
                        "enum": ["supervisor", "code_analyzer", "security_agent", "performance_agent"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority level",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional task metadata"
                    }
                },
                "required": ["description", "agent", "priority"]
            }
        ),
        
        Tool(
            name="kairos.getProjectConstitution",
            description="Get the project constitution with standards, patterns, and architectural decisions",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": "Specific constitution section",
                        "enum": ["architecture", "security", "coding_standards", "deployment", "all"]
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="kairos.analyzeCode",
            description="Analyze code with Kairos intelligence for quality, security, and compliance",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to analyze"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context information about the code"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis to perform",
                        "enum": ["quality", "security", "performance", "architecture", "all"]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path for context"
                    }
                },
                "required": ["code"]
            }
        ),
        
        Tool(
            name="kairos.getSuggestions",
            description="Get proactive suggestions from Kairos Supervisor Agent",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Scope of suggestions",
                        "enum": ["code", "architecture", "security", "performance", "testing", "all"]
                    },
                    "context": {
                        "type": "object",
                        "description": "Current context for suggestions",
                        "properties": {
                            "current_file": {"type": "string"},
                            "current_function": {"type": "string"},
                            "recent_changes": {"type": "array"}
                        }
                    }
                },
                "required": ["scope"]
            }
        ),
        
        Tool(
            name="kairos.getSystemHealth",
            description="Get current system health status from Supervisor Agent",
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
        )
    ]
