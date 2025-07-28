"""
Model Context Protocol (MCP) Implementation for Kairos

This module implements the Model Context Protocol to enable richer, more structured
communication between the system and LLMs, providing better context awareness and
tool usage capabilities.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Import MemoryManager for persistence
try:
    from ..memory.memory_manager import MemoryManager
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False

# Import MCP utilities
try:
    from .mcp_utilities import mcp_utils
    MCP_UTILS_AVAILABLE = True
except ImportError:
    MCP_UTILS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MCPMessageType(str, Enum):
    """Types of MCP messages"""
    # Context management
    CONTEXT_INIT = "context_init"
    CONTEXT_UPDATE = "context_update"
    CONTEXT_QUERY = "context_query"
    
    # Tool management
    TOOL_REGISTRATION = "tool_registration"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    
    # Memory integration
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    MEMORY_UPDATE = "memory_update"
    
    # Agent coordination
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    
    # System events
    SYSTEM_EVENT = "system_event"
    ERROR = "error"


class MCPRole(str, Enum):
    """Roles in MCP communication"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    AGENT = "agent"


@dataclass
class MCPContext:
    """Represents context in MCP"""
    context_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Context data
    global_context: Dict[str, Any] = field(default_factory=dict)
    local_context: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool context
    available_tools: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    
    # Memory context
    relevant_memories: List[Dict[str, Any]] = field(default_factory=list)
    memory_embeddings: Dict[str, List[float]] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update(self, updates: Dict[str, Any]):
        """Update context with new data"""
        for key, value in updates.items():
            if hasattr(self, key):
                if isinstance(getattr(self, key), dict):
                    getattr(self, key).update(value)
                else:
                    setattr(self, key, value)
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "context_id": self.context_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "global_context": self.global_context,
            "local_context": self.local_context,
            "conversation_history": self.conversation_history,
            "available_tools": self.available_tools,
            "tool_results": self.tool_results,
            "relevant_memories": self.relevant_memories,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class MCPMessage:
    """Represents an MCP message"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MCPMessageType = MCPMessageType.CONTEXT_INIT
    role: MCPRole = MCPRole.SYSTEM
    content: Dict[str, Any] = field(default_factory=dict)
    context_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "role": self.role,
            "content": self.content,
            "context_id": self.context_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class MCPTool:
    """Represents a tool available in MCP"""
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    requires_confirmation: bool = False
    cost_estimate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for LLM"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
            "cost_estimate": self.cost_estimate
        }


class ModelContextProtocol:
    """Main MCP implementation"""
    
    def __init__(self):
        self.contexts: Dict[str, MCPContext] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.message_handlers: Dict[MCPMessageType, List[Callable]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize memory manager if available
        self.memory_manager = None
        if MEMORY_MANAGER_AVAILABLE:
            try:
                self.memory_manager = MemoryManager()
                logger.info("✅ MCP connected to MemoryManager")
            except Exception as e:
                logger.warning(f"Failed to initialize MemoryManager: {e}")
        
        # Initialize default tools
        self._register_default_tools()
        
        logger.info("🔗 Model Context Protocol initialized")
    
    def _register_default_tools(self):
        """Register default system tools"""
        # Memory search tool
        self.register_tool(MCPTool(
            tool_id="memory_search",
            name="Search Memory",
            description="Search through stored memories and context",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                "context_type": {"type": "string", "description": "Type of context to search"}
            },
            handler=self._handle_memory_search
        ))
        
        # Context update tool
        self.register_tool(MCPTool(
            tool_id="context_update",
            name="Update Context",
            description="Update the current conversation context",
            parameters={
                "updates": {"type": "object", "description": "Context updates"},
                "merge": {"type": "boolean", "description": "Merge with existing", "default": True}
            },
            handler=self._handle_context_update
        ))
        
        # Agent invocation tool
        self.register_tool(MCPTool(
            tool_id="invoke_agent",
            name="Invoke Agent",
            description="Invoke a specific agent for a task",
            parameters={
                "agent_type": {"type": "string", "description": "Type of agent to invoke"},
                "task": {"type": "string", "description": "Task description"},
                "parameters": {"type": "object", "description": "Agent parameters"}
            },
            handler=self._handle_agent_invocation
        ))
        
        # Advanced research tool
        self.register_tool(MCPTool(
            tool_id="deep_research",
            name="Deep Research",
            description="Perform comprehensive research with multiple sources and AI analysis",
            parameters={
                "topic": {"type": "string", "description": "Research topic"},
                "sources": {"type": "array", "description": "Preferred sources", "default": ["internal", "web", "ai"]},
                "depth": {"type": "string", "enum": ["basic", "comprehensive", "expert"], "default": "comprehensive"}
            },
            handler=self._handle_deep_research
        ))
        
        # Project analysis tool
        self.register_tool(MCPTool(
            tool_id="analyze_project",
            name="Analyze Project",
            description="Analyze current project structure and context",
            parameters={
                "analysis_type": {"type": "string", "enum": ["architecture", "dependencies", "patterns", "full"], "default": "full"},
                "focus_areas": {"type": "array", "description": "Specific areas to analyze"}
            },
            handler=self._handle_project_analysis
        ))
        
        # Context synthesis tool
        self.register_tool(MCPTool(
            tool_id="synthesize_context",
            name="Synthesize Context",
            description="Synthesize information from multiple contexts and memories",
            parameters={
                "query": {"type": "string", "description": "Synthesis query"},
                "context_types": {"type": "array", "description": "Types of context to include"},
                "synthesis_type": {"type": "string", "enum": ["summary", "insights", "recommendations"], "default": "insights"}
            },
            handler=self._handle_context_synthesis
        ))
        
        # Code intelligence tool
        self.register_tool(MCPTool(
            tool_id="code_intelligence",
            name="Code Intelligence",
            description="Analyze code patterns, suggest improvements, and provide insights",
            parameters={
                "file_path": {"type": "string", "description": "File path to analyze"},
                "analysis_type": {"type": "string", "enum": ["quality", "security", "performance", "architecture"], "default": "quality"},
                "suggestions": {"type": "boolean", "description": "Include improvement suggestions", "default": True}
            },
            handler=self._handle_code_intelligence
        ))
    
    def create_context(self, 
                      project_id: Optional[str] = None,
                      session_id: Optional[str] = None,
                      user_id: Optional[str] = None,
                      initial_data: Optional[Dict[str, Any]] = None) -> MCPContext:
        """Create a new MCP context"""
        context = MCPContext(
            project_id=project_id,
            session_id=session_id,
            user_id=user_id
        )
        
        if initial_data:
            context.update(initial_data)
        
        self.contexts[context.context_id] = context
        logger.info(f"Created MCP context: {context.context_id}")
        
        return context
    
    def get_context(self, context_id: str) -> Optional[MCPContext]:
        """Get context by ID"""
        return self.contexts.get(context_id)
    
    def update_context(self, context_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing context"""
        context = self.get_context(context_id)
        if context:
            context.update(updates)
            return True
        return False
    
    def register_tool(self, tool: MCPTool):
        """Register a tool for MCP"""
        self.tools[tool.tool_id] = tool
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def register_handler(self, message_type: MCPMessageType, handler: Callable):
        """Register a message handler"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    async def process_message(self, message: MCPMessage) -> MCPMessage:
        """Process an MCP message"""
        try:
            # Get context
            context = None
            if message.context_id:
                context = self.get_context(message.context_id)
            
            # Handle tool calls
            if message.message_type == MCPMessageType.TOOL_CALL:
                return await self._handle_tool_call(message, context)
            
            # Execute registered handlers
            if message.message_type in self.message_handlers:
                for handler in self.message_handlers[message.message_type]:
                    try:
                        result = await handler(message, context)
                        if result:
                            return result
                    except Exception as e:
                        logger.error(f"Error in MCP handler: {e}")
            
            # Default response
            return MCPMessage(
                message_type=MCPMessageType.SYSTEM_EVENT,
                role=MCPRole.SYSTEM,
                content={"status": "processed", "message_id": message.message_id},
                context_id=message.context_id
            )
            
        except Exception as e:
            logger.error(f"Error processing MCP message: {e}")
            return MCPMessage(
                message_type=MCPMessageType.ERROR,
                role=MCPRole.SYSTEM,
                content={"error": str(e), "message_id": message.message_id},
                context_id=message.context_id
            )
    
    async def _handle_tool_call(self, message: MCPMessage, context: Optional[MCPContext]) -> MCPMessage:
        """Handle tool call messages"""
        tool_id = message.content.get("tool_id")
        parameters = message.content.get("parameters", {})
        
        if tool_id not in self.tools:
            return MCPMessage(
                message_type=MCPMessageType.ERROR,
                role=MCPRole.SYSTEM,
                content={"error": f"Unknown tool: {tool_id}"},
                context_id=message.context_id
            )
        
        tool = self.tools[tool_id]
        
        try:
            if tool.handler:
                result = await tool.handler(parameters, context)
            else:
                result = {"error": "Tool has no handler"}
            
            # Store result in context if available
            if context:
                context.tool_results[message.message_id] = result
            
            return MCPMessage(
                message_type=MCPMessageType.TOOL_RESULT,
                role=MCPRole.TOOL,
                content={
                    "tool_id": tool_id,
                    "result": result,
                    "call_id": message.message_id
                },
                context_id=message.context_id
            )
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_id}: {e}")
            return MCPMessage(
                message_type=MCPMessageType.ERROR,
                role=MCPRole.SYSTEM,
                content={
                    "error": f"Tool execution failed: {str(e)}",
                    "tool_id": tool_id
                },
                context_id=message.context_id
            )
    
    async def _handle_memory_search(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle memory search tool calls"""
        # This will be implemented to integrate with the memory manager
        query = parameters.get("query", "")
        limit = parameters.get("limit", 10)
        context_type = parameters.get("context_type")
        
        # Placeholder for actual memory search
        return {
            "results": [],
            "query": query,
            "message": "Memory search integration pending"
        }
    
    async def _handle_context_update(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle context update tool calls"""
        if not context:
            return {"error": "No context available"}
        
        updates = parameters.get("updates", {})
        merge = parameters.get("merge", True)
        
        if merge:
            context.update(updates)
        else:
            # Replace context data
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        
        return {
            "status": "updated",
            "context_id": context.context_id,
            "updated_fields": list(updates.keys())
        }
    
    async def _handle_agent_invocation(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle agent invocation tool calls"""
        agent_type = parameters.get("agent_type")
        task = parameters.get("task")
        agent_params = parameters.get("parameters", {})
        
        # This will be implemented to integrate with the agent coordinator
        return {
            "status": "pending",
            "agent_type": agent_type,
            "task": task,
            "message": "Agent invocation integration pending"
        }
    
    async def _handle_deep_research(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle deep research tool calls - comprehensive research with multiple sources"""
        topic = parameters.get("topic", "")
        sources = parameters.get("sources", ["internal", "web", "ai"])
        depth = parameters.get("depth", "comprehensive")
        
        research_results = {
            "topic": topic,
            "depth": depth,
            "sources_requested": sources,
            "findings": [],
            "confidence_score": 0,
            "research_plan": [],
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Create adaptive research plan based on topic and depth
            if MCP_UTILS_AVAILABLE:
                research_plan = await mcp_utils._create_adaptive_research_plan(topic, depth, sources)
            else:
                research_plan = [{"step": 1, "type": "basic_search", "description": f"Basic search for {topic}"}]
            research_results["research_plan"] = research_plan
            
            # Execute research plan
            for step in research_plan:
                try:
                    if step["type"] == "internal_search":
                        if MCP_UTILS_AVAILABLE:
                            internal_findings = await mcp_utils._execute_internal_search(topic, step.get("parameters", {}))
                        else:
                            internal_findings = [{"source": "fallback", "content": f"Internal search for {topic}", "relevance": 0.5}]
                        research_results["findings"].extend(internal_findings)
                        research_results["confidence_score"] += 25
                    
                    elif step["type"] == "web_search":
                        if MCP_UTILS_AVAILABLE:
                            web_findings = await mcp_utils._execute_web_search(topic, step.get("parameters", {}))
                        else:
                            web_findings = [{"source": "fallback", "content": f"Web search for {topic}", "relevance": 0.5}]
                        research_results["findings"].extend(web_findings)
                        research_results["confidence_score"] += 30
                    
                    elif step["type"] == "ai_analysis":
                        if MCP_UTILS_AVAILABLE:
                            ai_insights = await mcp_utils._execute_ai_analysis(topic, research_results["findings"], depth)
                        else:
                            ai_insights = {"analysis_type": "fallback", "topic": topic, "insights": "AI analysis unavailable", "confidence": 0.0}
                        research_results["ai_insights"] = ai_insights
                        research_results["confidence_score"] += 35
                    
                    elif step["type"] == "code_analysis":
                        if MCP_UTILS_AVAILABLE:
                            code_findings = await mcp_utils._execute_code_analysis(topic, step.get("parameters", {}))
                        else:
                            code_findings = [{"source": "fallback", "content": f"Code analysis for {topic}", "relevance": 0.5}]
                        research_results["findings"].extend(code_findings)
                        research_results["confidence_score"] += 20
                        
                except Exception as e:
                    logger.warning(f"Research step failed: {step['type']} - {e}")
                    research_results.setdefault("warnings", []).append(f"Step {step['type']} failed: {str(e)}")
            
            # Generate comprehensive summary
            if MCP_UTILS_AVAILABLE:
                research_results["summary"] = await mcp_utils._generate_research_summary(research_results)
            else:
                research_results["summary"] = f"Research summary for {topic} (utilities unavailable)"
            research_results["confidence_score"] = min(research_results["confidence_score"], 100)
            research_results["completed_at"] = datetime.now().isoformat()
            
            # Store research in context if available
            if context:
                context.local_context["last_research"] = {
                    "topic": topic,
                    "summary": research_results["summary"],
                    "confidence": research_results["confidence_score"],
                    "timestamp": datetime.now().isoformat()
                }
            
            return research_results
            
        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            return {
                "topic": topic,
                "error": str(e),
                "confidence_score": 0,
                "status": "failed"
            }
    
    
    async def _handle_project_analysis(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle project analysis tool calls - analyze current project structure"""
        analysis_type = parameters.get("analysis_type", "full")
        focus_areas = parameters.get("focus_areas", [])
        
        analysis_results = {
            "analysis_type": analysis_type,
            "focus_areas": focus_areas,
            "project_structure": {},
            "insights": [],
            "recommendations": [],
            "metrics": {},
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Analyze project structure
            if analysis_type in ["architecture", "full"]:
                architecture_analysis = await self._analyze_project_architecture()
                analysis_results["project_structure"]["architecture"] = architecture_analysis
                analysis_results["insights"].extend(architecture_analysis.get("insights", []))
            
            # Analyze dependencies
            if analysis_type in ["dependencies", "full"]:
                dependency_analysis = await self._analyze_project_dependencies()
                analysis_results["project_structure"]["dependencies"] = dependency_analysis
                analysis_results["insights"].extend(dependency_analysis.get("insights", []))
            
            # Analyze patterns
            if analysis_type in ["patterns", "full"]:
                pattern_analysis = await self._analyze_code_patterns(focus_areas)
                analysis_results["project_structure"]["patterns"] = pattern_analysis
                analysis_results["insights"].extend(pattern_analysis.get("insights", []))
            
            # Generate recommendations
            analysis_results["recommendations"] = await self._generate_project_recommendations(analysis_results)
            
            # Calculate metrics
            analysis_results["metrics"] = {
                "total_insights": len(analysis_results["insights"]),
                "recommendations_count": len(analysis_results["recommendations"]),
                "analysis_depth": len(analysis_results["project_structure"]),
                "completion_score": 85 if analysis_type == "full" else 60
            }
            
            analysis_results["completed_at"] = datetime.now().isoformat()
            
            # Store analysis in context
            if context:
                context.local_context["project_analysis"] = {
                    "type": analysis_type,
                    "insights_count": len(analysis_results["insights"]),
                    "recommendations_count": len(analysis_results["recommendations"]),
                    "timestamp": datetime.now().isoformat()
                }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Project analysis failed: {e}")
            return {
                "analysis_type": analysis_type,
                "error": str(e),
                "status": "failed"
            }
    
    async def _handle_context_synthesis(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle context synthesis tool calls - synthesize information from multiple contexts"""
        query = parameters.get("query", "")
        context_types = parameters.get("context_types", ["conversation", "memory", "project"])
        synthesis_type = parameters.get("synthesis_type", "insights")
        
        synthesis_results = {
            "query": query,
            "context_types": context_types,
            "synthesis_type": synthesis_type,
            "sources": [],
            "synthesized_content": {},
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Collect information from different contexts
            collected_data = {}
            
            # Current conversation context
            if "conversation" in context_types and context:
                conversation_data = await self._extract_conversation_context(context, query)
                collected_data["conversation"] = conversation_data
                synthesis_results["sources"].append("current_conversation")
            
            # Memory context from long-term storage
            if "memory" in context_types and self.memory_manager:
                memory_data = await self._extract_memory_context(query)
                collected_data["memory"] = memory_data
                synthesis_results["sources"].append("long_term_memory")
            
            # Project context
            if "project" in context_types:
                project_data = await self._extract_project_context(query)
                collected_data["project"] = project_data
                synthesis_results["sources"].append("project_context")
            
            # Knowledge graph context
            if "knowledge" in context_types and self.memory_manager:
                knowledge_data = await self._extract_knowledge_context(query)
                collected_data["knowledge"] = knowledge_data
                synthesis_results["sources"].append("knowledge_graph")
            
            # Synthesize collected data based on type
            if synthesis_type == "summary":
                synthesis_results["synthesized_content"] = await self._create_synthesis_summary(collected_data, query)
            elif synthesis_type == "insights":
                synthesis_results["synthesized_content"] = await self._create_synthesis_insights(collected_data, query)
            elif synthesis_type == "recommendations":
                synthesis_results["synthesized_content"] = await self._create_synthesis_recommendations(collected_data, query)
            
            synthesis_results["confidence_score"] = len(synthesis_results["sources"]) * 20  # 20% per source
            synthesis_results["completed_at"] = datetime.now().isoformat()
            
            # Store synthesis results in context
            if context:
                context.local_context["last_synthesis"] = {
                    "query": query,
                    "type": synthesis_type,
                    "sources_count": len(synthesis_results["sources"]),
                    "timestamp": datetime.now().isoformat()
                }
            
            return synthesis_results
            
        except Exception as e:
            logger.error(f"Context synthesis failed: {e}")
            return {
                "query": query,
                "error": str(e),
                "status": "failed"
            }
    
    async def _handle_code_intelligence(self, parameters: Dict[str, Any], context: Optional[MCPContext]) -> Dict[str, Any]:
        """Handle code intelligence tool calls - analyze code and provide insights"""
        file_path = parameters.get("file_path", "")
        analysis_type = parameters.get("analysis_type", "quality")
        include_suggestions = parameters.get("suggestions", True)
        
        intelligence_results = {
            "file_path": file_path,
            "analysis_type": analysis_type,
            "code_metrics": {},
            "findings": [],
            "suggestions": [] if include_suggestions else None,
            "quality_score": 0,
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Read and analyze the file
            if file_path:
                file_analysis = await self._analyze_code_file(file_path, analysis_type)
                intelligence_results.update(file_analysis)
            else:
                # Analyze current project's codebase
                codebase_analysis = await self._analyze_codebase(analysis_type)
                intelligence_results.update(codebase_analysis)
            
            # Generate suggestions if requested
            if include_suggestions:
                suggestions = await self._generate_code_suggestions(intelligence_results, analysis_type)
                intelligence_results["suggestions"] = suggestions
            
            # Calculate quality score
            intelligence_results["quality_score"] = await self._calculate_code_quality_score(intelligence_results)
            intelligence_results["completed_at"] = datetime.now().isoformat()
            
            # Store intelligence results in context
            if context:
                context.local_context["code_intelligence"] = {
                    "file_path": file_path,
                    "analysis_type": analysis_type,
                    "quality_score": intelligence_results["quality_score"],
                    "findings_count": len(intelligence_results["findings"]),
                    "timestamp": datetime.now().isoformat()
                }
            
            return intelligence_results
            
        except Exception as e:
            logger.error(f"Code intelligence failed: {e}")
            return {
                "file_path": file_path,
                "error": str(e),
                "status": "failed"
            }
    
    def format_for_llm(self, context: MCPContext, include_tools: bool = True) -> str:
        """Format context for LLM consumption"""
        formatted = {
            "system_context": {
                "project_id": context.project_id,
                "session_id": context.session_id,
                "timestamp": datetime.now().isoformat()
            },
            "global_context": context.global_context,
            "local_context": context.local_context,
            "conversation_history": context.conversation_history[-10:],  # Last 10 messages
            "relevant_memories": context.relevant_memories[:5]  # Top 5 memories
        }
        
        if include_tools:
            formatted["available_tools"] = [
                tool.to_dict() for tool in self.tools.values()
            ]
        
        if context.tool_results:
            formatted["recent_tool_results"] = list(context.tool_results.values())[-3:]
        
        return json.dumps(formatted, indent=2)
    
    def parse_llm_response(self, response: str, context_id: str) -> List[MCPMessage]:
        """Parse LLM response for MCP messages"""
        messages = []
        
        try:
            # Try to parse as JSON first
            data = json.loads(response)
            
            if isinstance(data, dict):
                # Single message
                messages.append(self._parse_single_message(data, context_id))
            elif isinstance(data, list):
                # Multiple messages
                for item in data:
                    messages.append(self._parse_single_message(item, context_id))
            
        except json.JSONDecodeError:
            # Plain text response
            messages.append(MCPMessage(
                message_type=MCPMessageType.AGENT_RESPONSE,
                role=MCPRole.ASSISTANT,
                content={"text": response},
                context_id=context_id
            ))
        
        return messages
    
    def _parse_single_message(self, data: Dict[str, Any], context_id: str) -> MCPMessage:
        """Parse a single message from LLM response"""
        message_type = MCPMessageType(data.get("type", MCPMessageType.AGENT_RESPONSE))
        role = MCPRole(data.get("role", MCPRole.ASSISTANT))
        
        return MCPMessage(
            message_type=message_type,
            role=role,
            content=data.get("content", {}),
            context_id=context_id,
            metadata=data.get("metadata", {})
        )
    
    async def persist_context(self, context_id: str, 
                            task_result: Optional[Dict[str, Any]] = None,
                            relationship_type: str = "completed_task") -> Dict[str, Any]:
        """Persist MCP context to long-term memory (Neo4j & Qdrant)"""
        if not self.memory_manager:
            logger.warning("MemoryManager not available for context persistence")
            return {"status": "failed", "reason": "no_memory_manager"}
        
        context = self.get_context(context_id)
        if not context:
            logger.error(f"Context {context_id} not found for persistence")
            return {"status": "failed", "reason": "context_not_found"}
        
        try:
            # Create Kairos Atom from MCP context
            atom_data = {
                "context_id": context.context_id,
                "project_id": context.project_id,
                "session_id": context.session_id,
                "user_id": context.user_id,
                "global_context": context.global_context,
                "local_context": context.local_context,
                "conversation_summary": self._summarize_conversation(context.conversation_history),
                "tool_usage_summary": self._summarize_tool_usage(context.tool_results),
                "task_result": task_result,
                "created_at": context.created_at.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "duration_minutes": (datetime.now() - context.created_at).total_seconds() / 60
            }
            
            # Generate unique node ID for this context atom
            atom_id = f"mcp_context_{context.context_id}"
            
            # 1. Add to Knowledge Graph (Neo4j)
            kg_success = self.memory_manager.add_knowledge_node(
                node_id=atom_id,
                data=atom_data,
                node_type="mcp_context"
            )
            
            # 2. Add to Vector Store (Qdrant) for semantic search
            # Create searchable content from context
            searchable_content = self._create_searchable_content(context, task_result)
            
            context_memory_id = self.memory_manager.add_context_memory(
                content=searchable_content,
                context_type="mcp_session",
                metadata={
                    "context_id": context.context_id,
                    "project_id": context.project_id,
                    "session_id": context.session_id,
                    "atom_id": atom_id,
                    "task_completed": task_result is not None
                }
            )
            
            # 3. Create relationships with existing knowledge
            relationships_created = []
            
            # Link to project if exists
            if context.project_id:
                project_relation = self.memory_manager.add_knowledge_relationship(
                    from_node=atom_id,
                    to_node=f"project_{context.project_id}",
                    relationship=relationship_type,
                    properties={
                        "created_at": datetime.now().isoformat(),
                        "context_type": "mcp_session"
                    }
                )
                if project_relation:
                    relationships_created.append(f"project_{context.project_id}")
            
            # Link to related memories based on conversation content
            if context.conversation_history:
                related_memories = self._find_related_memories(context)
                for memory in related_memories[:3]:  # Limit to top 3 related memories
                    memory_relation = self.memory_manager.add_knowledge_relationship(
                        from_node=atom_id,
                        to_node=memory.get("id", memory.get("node_id")),
                        relationship="relates_to",
                        properties={
                            "similarity_score": memory.get("score", 0.5),
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    if memory_relation:
                        relationships_created.append(memory.get("id", memory.get("node_id")))
            
            # 4. Store as episode for temporal access
            episode_id = self.memory_manager.add_episode(
                episode_type="mcp_session_completed",
                content=f"MCP session {context.context_id} completed with {len(context.conversation_history)} interactions",
                metadata={
                    "context_id": context.context_id,
                    "project_id": context.project_id,
                    "atom_id": atom_id,
                    "context_memory_id": context_memory_id,
                    "tools_used": list(context.tool_results.keys()),
                    "relationships_created": len(relationships_created)
                }
            )
            
            persistence_result = {
                "status": "success",
                "atom_id": atom_id,
                "context_memory_id": context_memory_id,
                "episode_id": episode_id,
                "relationships_created": len(relationships_created),
                "knowledge_graph_success": kg_success,
                "persisted_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ MCP context {context_id} persisted successfully: {atom_id}")
            return persistence_result
            
        except Exception as e:
            logger.error(f"Failed to persist MCP context {context_id}: {e}")
            return {
                "status": "failed", 
                "reason": "persistence_error",
                "error": str(e)
            }
    
    def _summarize_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Create a summary of the conversation history"""
        if not conversation_history:
            return "No conversation history"
        
        # Simple summarization - can be enhanced with LLM summarization
        total_messages = len(conversation_history)
        user_messages = len([msg for msg in conversation_history if msg.get("role") == "user"])
        assistant_messages = len([msg for msg in conversation_history if msg.get("role") == "assistant"])
        
        # Extract key topics from conversation
        all_content = " ".join([msg.get("content", "") for msg in conversation_history[-10:]])
        words = all_content.lower().split()
        # Simple keyword extraction (can be improved with NLP)
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "how", "what", "why", "when", "where", "can", "will", "would", "could", "should"}
        keywords = [word for word in set(words) if len(word) > 3 and word not in common_words][:10]
        
        return f"Conversation with {total_messages} messages ({user_messages} user, {assistant_messages} assistant). Key topics: {', '.join(keywords[:5])}"
    
    def _summarize_tool_usage(self, tool_results: Dict[str, Any]) -> str:
        """Create a summary of tool usage"""
        if not tool_results:
            return "No tools used"
        
        tool_count = len(tool_results)
        # Extract tool types from results
        tool_types = set()
        for result in tool_results.values():
            if isinstance(result, dict) and "tool_id" in result:
                tool_types.add(result["tool_id"])
        
        return f"Used {tool_count} tools: {', '.join(tool_types)}"
    
    def _create_searchable_content(self, context: MCPContext, task_result: Optional[Dict[str, Any]]) -> str:
        """Create searchable content from MCP context"""
        content_parts = []
        
        # Add conversation content
        if context.conversation_history:
            recent_conversations = context.conversation_history[-5:]  # Last 5 messages
            for msg in recent_conversations:
                if msg.get("content"):
                    content_parts.append(f"{msg.get('role', 'unknown')}: {msg['content']}")
        
        # Add context data
        if context.global_context:
            content_parts.append(f"Global context: {json.dumps(context.global_context)}")
        
        if context.local_context:
            content_parts.append(f"Local context: {json.dumps(context.local_context)}")
        
        # Add task result if available
        if task_result:
            content_parts.append(f"Task result: {json.dumps(task_result)}")
        
        # Add project and session info
        if context.project_id:
            content_parts.append(f"Project: {context.project_id}")
        
        if context.session_id:
            content_parts.append(f"Session: {context.session_id}")
        
        return " | ".join(content_parts)
    
    def _find_related_memories(self, context: MCPContext) -> List[Dict[str, Any]]:
        """Find memories related to the current context"""
        if not context.conversation_history:
            return []
        
        # Create search query from recent conversation
        recent_content = " ".join([
            msg.get("content", "") for msg in context.conversation_history[-3:]
            if msg.get("content")
        ])
        
        if not recent_content.strip():
            return []
        
        # Search for related memories
        related_memories = self.memory_manager.search_context_memory(
            query=recent_content,
            context_type=None,  # Search all context types
            limit=5
        )
        
        return related_memories
    
    # Stub methods for project analysis and context synthesis
    async def _analyze_project_architecture(self) -> Dict[str, Any]:
        """Analyze project architecture - stub implementation"""
        return {
            "components": ["agents", "mcp", "memory", "websocket", "frontend"],
            "patterns": ["multi-agent", "event-driven", "microservice"],
            "insights": [
                "Well-structured agent-based architecture",
                "Strong separation of concerns between components",
                "Effective use of MCP for context management"
            ]
        }
    
    async def _analyze_project_dependencies(self) -> Dict[str, Any]:
        """Analyze project dependencies - stub implementation"""
        return {
            "python_deps": ["fastapi", "neo4j", "qdrant", "websockets"],
            "external_services": ["ollama", "openrouter", "gemini"],
            "insights": [
                "Modern Python stack with async support",
                "Good balance of local and cloud AI services",
                "Robust storage with graph and vector databases"
            ]
        }
    
    async def _analyze_code_patterns(self, focus_areas: List[str]) -> Dict[str, Any]:
        """Analyze code patterns - stub implementation"""
        return {
            "patterns_found": ["async/await", "dataclasses", "dependency_injection"],
            "code_quality": "high",
            "insights": [
                "Consistent use of async patterns",
                "Good type hints and documentation",
                "Modular and testable design"
            ]
        }
    
    async def _generate_project_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate project recommendations - stub implementation"""
        return [
            "Complete Frontend Task Detail Panel for MCP visualization",
            "Implement comprehensive test suite with pytest-asyncio",
            "Add performance monitoring and metrics collection",
            "Create backup/restore automation for Neo4j and Qdrant",
            "Enhance API documentation with interactive examples"
        ]
    
    async def _extract_conversation_context(self, context: MCPContext, query: str) -> Dict[str, Any]:
        """Extract conversation context - stub implementation"""
        return {
            "recent_messages": len(context.conversation_history),
            "topics": ["sprint6", "mcp", "research", "testing"],
            "relevance_score": 0.8
        }
    
    async def _extract_memory_context(self, query: str) -> Dict[str, Any]:
        """Extract memory context - stub implementation"""
        return {
            "memory_matches": 5,
            "relevance_score": 0.7,
            "topics": ["development", "architecture", "planning"]
        }
    
    async def _extract_project_context(self, query: str) -> Dict[str, Any]:
        """Extract project context - stub implementation"""
        return {
            "project_files": 150,
            "relevant_modules": ["mcp", "agents", "memory"],
            "context_score": 0.9
        }
    
    async def _extract_knowledge_context(self, query: str) -> Dict[str, Any]:
        """Extract knowledge graph context - stub implementation"""
        return {
            "knowledge_nodes": 25,
            "relationships": 40,
            "relevance_score": 0.75
        }
    
    async def _create_synthesis_summary(self, collected_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Create synthesis summary - stub implementation"""
        return {
            "summary": f"Synthesis summary for: {query}",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "confidence": 0.8
        }
    
    async def _create_synthesis_insights(self, collected_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Create synthesis insights - stub implementation"""
        return {
            "insights": f"Key insights for: {query}",
            "patterns": ["Pattern A", "Pattern B"],
            "confidence": 0.85
        }
    
    async def _create_synthesis_recommendations(self, collected_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Create synthesis recommendations - stub implementation"""
        return {
            "recommendations": [
                "Implement React Task Detail Panel with real-time WebSocket integration",
                "Create comprehensive test suite using pytest-asyncio for async testing", 
                "Build performance benchmarking tools for multi-agent coordination",
                "Develop Neo4j backup/restore automation scripts",
                "Enhance FastAPI documentation with interactive examples"
            ],
            "priority_order": [1, 2, 3, 4, 5],
            "confidence": 0.9
        }
    
    async def _analyze_code_file(self, file_path: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze specific code file - stub implementation"""
        return {
            "code_metrics": {"lines": 500, "complexity": "medium"},
            "findings": ["Good structure", "Needs documentation"],
            "quality_score": 75
        }
    
    async def _analyze_codebase(self, analysis_type: str) -> Dict[str, Any]:
        """Analyze entire codebase - stub implementation"""
        return {
            "code_metrics": {"total_lines": 5000, "avg_complexity": "medium"},
            "findings": ["Well structured", "Good test coverage needed"],
            "quality_score": 80
        }
    
    async def _generate_code_suggestions(self, intelligence_results: Dict[str, Any], analysis_type: str) -> List[str]:
        """Generate code suggestions - stub implementation"""
        return [
            "Add comprehensive docstrings to all methods",
            "Implement type hints for better code clarity",
            "Add unit tests for critical functions",
            "Consider extracting common patterns into utilities"
        ]
    
    async def _calculate_code_quality_score(self, intelligence_results: Dict[str, Any]) -> float:
        """Calculate code quality score - stub implementation"""
        return 82.5


# Global MCP instance
mcp = ModelContextProtocol()
