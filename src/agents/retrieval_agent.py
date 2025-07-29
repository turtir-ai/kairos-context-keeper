import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.llm_router import LLMRouter
from src.agents.base_agent import BaseAgent

# Phase 2: Deep Memory Integration
try:
    from src.services.context_service import get_enriched_context
    CONTEXT_SERVICE_AVAILABLE = True
except ImportError:
    CONTEXT_SERVICE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Context Service not available - using fallback retrieval")

class RetrievalAgent(BaseAgent):
    """Agent responsible for retrieving relevant context and information"""
    
    def __init__(self):
        super().__init__("RetrievalAgent")
        self.llm_router = LLMRouter()
        self.knowledge_base = {
            "project_info": {
                "name": "Kairos: The Context Keeper",
                "description": "Autonomous development supervisor powered by context engineering",
                "key_features": [
                    "Context Engineering Core",
                    "Agent Guild Architecture", 
                    "Self-Improving System",
                    "Hybrid Cloud/Local Infrastructure"
                ],
                "tech_stack": ["Python", "FastAPI", "Neo4j", "Qdrant", "Ollama", "Docker"]
            },
            "development_patterns": {
                "architecture": "Agent-based with context preservation",
                "memory_layers": ["Working Memory", "Episodic Memory", "Long-term Knowledge Graph"],
                "ai_routing": "Task-specific model selection with performance tracking"
            }
        }
        
    async def retrieve(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """Retrieve relevant information for a query using AI-enhanced search"""
        self.logger.info(f"🔍 Retrieving information for: {query}")
        print(f"🔍 Retrieving information for: {query}")
        
        # Step 1: Search local knowledge base
        local_results = self._search_local_knowledge(query)
        
        # Step 2: Use AI to enhance and contextualize results
        ai_enhanced_results = await self._ai_enhance_results(query, local_results)
        
        result = {
            "query": query,
            "local_results": local_results,
            "ai_enhanced": ai_enhanced_results,
            "retrieved_at": datetime.now().isoformat(),
            "agent": self.name
        }
        
        return result
    
    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retrieval task with enhanced context service integration"""
        task_type = task_params.get("type", "retrieve")
        
        if task_type == "deep_analysis" and task_params.get("use_context_service"):
            return await self._execute_deep_analysis(task_params)
        else:
            # Standard retrieval
            query = task_params.get("query", task_params.get("description", ""))
            return await self.retrieve(query, task_params)
    
    async def _execute_deep_analysis(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deep analysis using Context Service - Phase 2 Implementation"""
        query = task_params.get("query", task_params.get("description", ""))
        analysis_type = task_params.get("analysis_type", "general")
        
        self.logger.info(f"🧠 Executing deep analysis: {analysis_type} - {query}")
        
        if CONTEXT_SERVICE_AVAILABLE:
            try:
                # Use Context Service for intelligent retrieval
                context_response = await get_enriched_context(
                    query=query,
                    depth="detailed",
                    max_tokens=4000,
                    include_code=True,
                    include_history=True
                )
                
                # Enhanced result with deep context
                result = {
                    "task_type": "deep_analysis",
                    "analysis_type": analysis_type,
                    "query": query,
                    "deep_context": {
                        "enriched_content": context_response.enriched_context,
                        "sources": context_response.sources,
                        "confidence_score": context_response.confidence_score,
                        "token_count": context_response.token_count,
                        "cache_hit": context_response.cache_hit,
                        "generated_at": context_response.generated_at.isoformat()
                    },
                    "analysis_summary": f"Deep analysis completed using {len(context_response.sources)} sources",
                    "actionable_insights": self._extract_actionable_insights(context_response.enriched_context, analysis_type),
                    "success": True,
                    "agent": self.name,
                    "executed_at": datetime.now().isoformat()
                }
                
                self.logger.info(f"✅ Deep analysis completed with confidence: {context_response.confidence_score}")
                return result
                
            except Exception as e:
                self.logger.error(f"❌ Deep analysis failed: {e}")
                return {
                    "task_type": "deep_analysis",
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "fallback_used": True,
                    "agent": self.name,
                    "executed_at": datetime.now().isoformat()
                }
        else:
            # Fallback without Context Service
            fallback_result = await self.retrieve(query)
            fallback_result.update({
                "task_type": "deep_analysis_fallback",
                "analysis_type": analysis_type,
                "note": "Context Service unavailable - used standard retrieval"
            })
            return fallback_result
    
    def _extract_actionable_insights(self, enriched_content: str, analysis_type: str) -> List[str]:
        """Extract actionable insights from enriched context"""
        insights = []
        
        if analysis_type == "structural":
            insights = [
                "Review component relationships for optimization opportunities",
                "Consider dependency injection improvements",
                "Evaluate circular dependency risks",
                "Assess architectural pattern consistency"
            ]
        elif analysis_type == "semantic":
            insights = [
                "Identify code patterns for standardization",
                "Review implementation approaches for consistency",
                "Consider best practice adoption",
                "Evaluate performance optimization opportunities"
            ]
        elif analysis_type == "performance":
            insights = [
                "Implement async optimization where applicable",
                "Review database query efficiency",
                "Consider caching strategies",
                "Monitor resource usage patterns"
            ]
        else:
            insights = [
                "Review system architecture for improvements",
                "Consider performance and security implications",
                "Evaluate maintainability factors",
                "Plan incremental enhancements"
            ]
        
        return insights
        
    def _search_local_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search through local knowledge base"""
        query_lower = query.lower()
        results = []
        
        # Search through different knowledge categories
        for category, data in self.knowledge_base.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    if any(term in str(value).lower() for term in query_lower.split()):
                        results.append({
                            "category": category,
                            "key": key,
                            "content": value,
                            "relevance_score": self._calculate_relevance(query_lower, str(value).lower())
                        })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:5]  # Return top 5 results
        
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Simple relevance scoring based on keyword matches"""
        query_terms = set(query.split())
        content_terms = set(content.split())
        
        if not query_terms:
            return 0.0
            
        matches = len(query_terms.intersection(content_terms))
        return matches / len(query_terms)
        
    async def _ai_enhance_results(self, query: str, local_results: List[Dict]) -> Dict[str, Any]:
        """Use AI to enhance and contextualize search results"""
        if not local_results:
            # If no local results, use AI to generate helpful context
            prompt = f"""As a context keeper for the Kairos project, provide helpful information about: {query}
            
Kairos is an autonomous development supervisor that uses:
            - Context engineering for maintaining project consistency
            - Agent-based architecture with specialized roles
            - AI routing for optimal model selection
            - Memory management with knowledge graphs
            
Provide a concise, helpful response about the query in the context of software development and AI assistance."""
        else:
            # Enhance existing results with AI context
            results_text = "\n".join([f"- {r['key']}: {r['content']}" for r in local_results])
            prompt = f"""Based on this retrieved information about '{query}':

{results_text}

Provide a clear, concise summary that helps understand how this relates to the Kairos project and software development. Focus on practical implications and next steps."""
            
        try:
            ai_response = await self.llm_router.generate(prompt)
            return {
                "summary": ai_response.get("response", "AI enhancement not available"),
                "model_used": ai_response.get("model_config", {}),
                "duration": ai_response.get("duration", 0)
            }
        except Exception as e:
            self.logger.error(f"AI enhancement failed: {e}")
            return {
                "summary": "AI enhancement temporarily unavailable",
                "error": str(e)
            }
            
    def add_knowledge(self, category: str, key: str, content: Any):
        """Add new knowledge to the local knowledge base"""
        if category not in self.knowledge_base:
            self.knowledge_base[category] = {}
        self.knowledge_base[category][key] = content
        self.logger.info(f"Added knowledge: {category}.{key}")
        
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of available knowledge"""
        return {
            "total_categories": len(self.knowledge_base),
            "categories": list(self.knowledge_base.keys()),
            "total_entries": sum(len(v) if isinstance(v, dict) else 1 for v in self.knowledge_base.values()),
            "last_updated": datetime.now().isoformat()
        }
        
    def get_status(self):
        return {
            "name": self.name,
            "status": self.status,
            "knowledge_summary": self.get_knowledge_summary(),
            "llm_available": True,  # Assume Ollama is available if router is initialized
            "last_activity": datetime.now().isoformat()
        }
