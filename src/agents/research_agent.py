import logging
import requests
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.llm_router import LLMRouter
from .base_agent import BaseAgent

# Import research tools (optional)
try:
    from .tools.research_tools import WebSearchTool, LocalKnowledgeTool, AIAnalysisTool
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    WebSearchTool = None
    LocalKnowledgeTool = None
    AIAnalysisTool = None

# Import MCP for context management
try:
    from src.mcp.model_context_protocol import MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class ResearchAgent(BaseAgent):
    """Agent responsible for researching topics and gathering information"""
    
    def __init__(self, mcp_context: Optional['MCPContext'] = None):
        super().__init__("ResearchAgent", mcp_context)
        self.logger = logging.getLogger(__name__)
        self.llm_router = LLMRouter()
        
        # Research sources configuration
        self.research_sources = {
            "internal": {
                "project_docs": [".kiro/steering.md", ".kiro/specs.md", "README.md"],
                "code_files": ["src/"],
                "description": "Internal project knowledge base"
            },
            "ai_analysis": {
                "enabled": True,
                "models": ["llama3.1:8b", "mistral:latest"],
                "description": "AI-powered topic analysis and summarization"
            }
        }
        
    async def research(self, topic: str, context: Dict = None) -> Dict[str, Any]:
        """Research a topic using multiple sources and AI analysis"""
        self.logger.info(f"🔍 Starting research on: {topic}")
        print(f"🔍 Starting research on: {topic}")
        
        research_results = {
            "topic": topic,
            "sources_used": [],
            "findings": [],
            "ai_analysis": None,
            "confidence_score": 0,
            "researched_at": datetime.now().isoformat(),
            "agent": self.name,
            "research_plan": [],
            "external_sources": []
        }
        
        try:
            # 0. Create research plan
            research_plan = await self._create_research_plan(topic, context)
            research_results["research_plan"] = research_plan
            self.logger.info(f"📋 Research plan created with {len(research_plan)} steps")
            
            # 1. Internal knowledge search
            internal_findings = await self._search_internal_knowledge(topic)
            if internal_findings:
                research_results["findings"].extend(internal_findings)
                research_results["sources_used"].append("internal")
                research_results["confidence_score"] += 20
            
            # 2. External web search
            if any(step["type"] == "web_search" for step in research_plan):
                web_findings = await self._search_external_sources(topic, research_plan)
                if web_findings:
                    research_results["findings"].extend(web_findings)
                    research_results["sources_used"].append("web")
                    research_results["external_sources"] = [f["url"] for f in web_findings if "url" in f]
                    research_results["confidence_score"] += 30
            
            # 3. AI-powered analysis
            if self.research_sources["ai_analysis"]["enabled"]:
                all_findings = internal_findings + (web_findings if 'web_findings' in locals() else [])
                ai_analysis = await self._ai_analyze_topic(topic, all_findings)
                research_results["ai_analysis"] = ai_analysis
                research_results["sources_used"].append("ai_analysis")
                research_results["confidence_score"] += 30
            
            # 4. Generate comprehensive summary
            summary = await self._generate_research_summary(topic, research_results)
            research_results["summary"] = summary
            research_results["confidence_score"] = min(research_results["confidence_score"] + 20, 100)
            
            self.logger.info(f"✅ Research completed with confidence: {research_results['confidence_score']}%")
            print(f"✅ Research completed with confidence: {research_results['confidence_score']}%")
            
        except Exception as e:
            self.logger.error(f"Research failed: {e}")
            research_results["error"] = str(e)
            research_results["confidence_score"] = 0
            
        return research_results
        
    async def _search_internal_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """Search internal project knowledge for topic-related information"""
        findings = []
        
        # Search in project documentation
        doc_files = [".kiro/steering.md", ".kiro/specs.md", "README.md", "SETUP.md"]
        
        for doc_file in doc_files:
            try:
                if os.path.exists(doc_file):
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Simple keyword matching
                    topic_words = topic.lower().split()
                    if any(word in content.lower() for word in topic_words):
                        findings.append({
                            "source": doc_file,
                            "type": "documentation",
                            "relevance": self._calculate_relevance(topic.lower(), content.lower()),
                            "excerpt": content[:500] + "..." if len(content) > 500 else content
                        })
            except Exception as e:
                self.logger.warning(f"Could not read {doc_file}: {e}")
        
        # Add some synthetic project knowledge
        kairos_knowledge = {
            "context engineering": "Core feature for maintaining project consistency through layered memory systems",
            "agent architecture": "Multi-agent system with Link, Retrieval, Execution, Guardian, and Research agents",
            "ai routing": "Intelligent model selection based on task type and performance metrics",
            "memory management": "Neo4j knowledge graphs combined with Qdrant vector storage",
            "ollama integration": "Local LLM execution with 40+ available models for cost-effective AI operations"
        }
        
        for key, description in kairos_knowledge.items():
            if any(word in key for word in topic.lower().split()):
                findings.append({
                    "source": "kairos_knowledge_base",
                    "type": "project_knowledge",
                    "relevance": 0.9,
                    "content": description
                })
        
        return findings
    
    async def _create_research_plan(self, topic: str, context: Dict = None) -> List[Dict[str, Any]]:
        """Create a research plan based on the topic"""
        plan = []
        
        # Always search internal knowledge first
        plan.append({
            "step": 1,
            "type": "internal_search",
            "description": f"Search project documentation for '{topic}'",
            "sources": ["docs", "code", "memory"]
        })
        
        # Determine if web search is needed
        web_keywords = ["latest", "trends", "news", "current", "2024", "2025", "best practices", "tutorial"]
        if any(keyword in topic.lower() for keyword in web_keywords):
            plan.append({
                "step": 2,
                "type": "web_search",
                "description": f"Search web for recent information about '{topic}'",
                "sources": ["wikipedia", "github", "tech_blogs"]
            })
        
        # AI analysis is always the final step
        plan.append({
            "step": len(plan) + 1,
            "type": "ai_synthesis",
            "description": "Synthesize findings with AI",
            "model": "llama3.1:8b"
        })
        
        return plan
    
    async def _search_external_sources(self, topic: str, research_plan: List[Dict]) -> List[Dict[str, Any]]:
        """Search external sources like Wikipedia and GitHub"""
        findings = []
        
        if not TOOLS_AVAILABLE or not WebSearchTool:
            self.logger.warning("Web search tools not available, skipping external search")
            return findings
        
        try:
            async with WebSearchTool() as search_tool:
                # Search Wikipedia
                wiki_results = await search_tool.search_wikipedia(topic, limit=2)
                for result in wiki_results:
                    findings.append({
                        "source": "Wikipedia",
                        "type": "external_web",
                        "title": result.get("title"),
                        "content": result.get("snippet"),
                        "url": result.get("url"),
                        "relevance": 0.8
                    })
                
                # Search GitHub for code examples
                if "code" in topic.lower() or "implementation" in topic.lower():
                    github_results = await search_tool.search_github(topic, limit=3)
                    for repo in github_results:
                        findings.append({
                            "source": "GitHub",
                            "type": "code_repository",
                            "title": repo.get("name"),
                            "content": repo.get("description", "No description"),
                            "url": repo.get("url"),
                            "stars": repo.get("stars", 0),
                            "language": repo.get("language"),
                            "relevance": 0.7
                        })
                
                self.logger.info(f"Found {len(findings)} external sources")
                
        except Exception as e:
            self.logger.error(f"External search failed: {e}")
            # Return empty findings on error but don't fail the entire research
            
        return findings
        
    async def _ai_analyze_topic(self, topic: str, internal_findings: List[Dict]) -> Dict[str, Any]:
        """Use AI to analyze the topic and provide insights"""
        # Prepare context from internal findings
        context_text = "\n".join([
            f"- {finding.get('content', finding.get('excerpt', ''))}" 
            for finding in internal_findings
        ])
        
        prompt = f"""As a research analyst for the Kairos project, analyze this topic: "{topic}"
        
Available context from project:
{context_text}

Provide a comprehensive analysis including:
1. Definition and key concepts
2. Relevance to software development
3. Implementation considerations
4. Best practices
5. Potential challenges

Keep the response concise but informative."""
        
        try:
            ai_response = await self.llm_router.generate(prompt)
            return {
                "analysis": ai_response.get("response", "AI analysis not available"),
                "model_used": ai_response.get("model_config", {}),
                "duration": ai_response.get("duration", 0)
            }
        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {
                "analysis": "AI analysis temporarily unavailable",
                "error": str(e)
            }
    
    async def _generate_research_summary(self, topic: str, research_data: Dict) -> str:
        """Generate a comprehensive research summary"""
        findings_count = len(research_data["findings"])
        sources_used = ", ".join(research_data["sources_used"])
        confidence = research_data["confidence_score"]
        
        summary = f"""Research Summary for '{topic}':
        
ℹ️ Found {findings_count} relevant sources
📊 Confidence Score: {confidence}%
📁 Sources Used: {sources_used}
        
Key findings from project context and AI analysis available.
        """
        
        return summary.strip()
        
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        query_words = set(query.split())
        content_words = set(content.split())
        
        if not query_words:
            return 0.0
            
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
        
    def get_status(self):
        # Use a simple check instead of async call
        return {
            "name": self.name,
            "status": self.status,
            "research_sources": list(self.research_sources.keys()),
            "llm_available": True,  # Assume Ollama is available if router is initialized
            "last_activity": datetime.now().isoformat()
        }
