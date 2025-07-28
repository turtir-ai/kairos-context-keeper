"""
MCP Utility Methods for Advanced Research and Analysis Tools

This module provides utility methods for MCP tool handlers to perform 
advanced research, project analysis, context synthesis, and code intelligence.
"""

import os
import ast
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)


class MCPUtilities:
    """Utility methods for MCP advanced tools"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        
    async def _create_adaptive_research_plan(self, topic: str, depth: str, sources: List[str]) -> List[Dict[str, Any]]:
        """Create an adaptive research plan based on topic and depth"""
        plan = []
        step_counter = 1
        
        # Always start with internal search
        plan.append({
            "step": step_counter,
            "type": "internal_search",
            "description": f"Search internal project knowledge for '{topic}'",
            "parameters": {
                "search_areas": ["docs", "code", "config", "memory"],
                "depth": "comprehensive" if depth == "expert" else "basic"
            },
            "estimated_time": "30s"
        })
        step_counter += 1
        
        # Web search for external sources
        if "web" in sources:
            web_keywords = ["latest", "current", "2024", "2025", "trends", "best practices", "tutorial", "guide"]
            if any(keyword in topic.lower() for keyword in web_keywords) or depth in ["comprehensive", "expert"]:
                plan.append({
                    "step": step_counter,
                    "type": "web_search",
                    "description": f"Search web sources for recent information about '{topic}'",
                    "parameters": {
                        "sources": ["wikipedia", "github", "technical_blogs"],
                        "limit": 5 if depth == "expert" else 3
                    },
                    "estimated_time": "60s"
                })
                step_counter += 1
        
        # Code analysis for technical topics
        tech_keywords = ["code", "implementation", "algorithm", "architecture", "pattern", "framework", "library"]
        if any(keyword in topic.lower() for keyword in tech_keywords):
            plan.append({
                "step": step_counter,
                "type": "code_analysis",
                "description": f"Analyze codebase for patterns related to '{topic}'",
                "parameters": {
                    "analysis_type": "patterns",
                    "focus_areas": [topic]
                },
                "estimated_time": "45s"
            })
            step_counter += 1
        
        # AI analysis for synthesis (always last)
        if "ai" in sources:
            plan.append({
                "step": step_counter,
                "type": "ai_analysis",
                "description": f"AI-powered synthesis and analysis of '{topic}' findings",
                "parameters": {
                    "analysis_depth": depth,
                    "synthesis_type": "comprehensive" if depth == "expert" else "summary"
                },
                "estimated_time": "90s" if depth == "expert" else "60s"
            })
        
        return plan
    
    async def _execute_internal_search(self, topic: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute internal project search"""
        findings = []
        search_areas = parameters.get("search_areas", ["docs", "code"])
        depth = parameters.get("depth", "basic")
        
        try:
            # Search project documentation
            if "docs" in search_areas:
                doc_findings = await self._search_project_docs(topic, depth)
                findings.extend(doc_findings)
            
            # Search codebase
            if "code" in search_areas:
                code_findings = await self._search_codebase(topic, depth)
                findings.extend(code_findings)
            
            # Search configuration files
            if "config" in search_areas:
                config_findings = await self._search_config_files(topic)
                findings.extend(config_findings)
            
            # Add Kairos-specific knowledge
            kairos_findings = self._get_kairos_knowledge(topic)
            findings.extend(kairos_findings)
            
        except Exception as e:
            logger.error(f"Internal search failed: {e}")
            findings.append({
                "source": "internal_search_error",
                "content": f"Search failed: {str(e)}",
                "relevance": 0.0
            })
        
        return findings
    
    async def _execute_web_search(self, topic: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute web search using available tools"""
        findings = []
        sources = parameters.get("sources", ["wikipedia"])
        limit = parameters.get("limit", 3)
        
        try:
            # Import research tools if available
            from ..agents.tools.research_tools import WebSearchTool
            
            async with WebSearchTool() as search_tool:
                # Wikipedia search
                if "wikipedia" in sources:
                    wiki_results = await search_tool.search_wikipedia(topic, limit=min(limit, 2))
                    for result in wiki_results:
                        findings.append({
                            "source": "wikipedia",
                            "type": "external_knowledge",
                            "title": result.get("title"),
                            "content": result.get("snippet"),
                            "url": result.get("url"),
                            "relevance": 0.8
                        })
                
                # GitHub search for code-related topics
                if "github" in sources and any(keyword in topic.lower() for keyword in ["code", "library", "framework", "implementation"]):
                    github_results = await search_tool.search_github(topic, limit=min(limit, 3))
                    for result in github_results:
                        findings.append({
                            "source": "github",
                            "type": "code_repository",
                            "name": result.get("name"),
                            "content": result.get("description"),
                            "url": result.get("url"),
                            "stars": result.get("stars"),
                            "language": result.get("language"),
                            "relevance": 0.7
                        })
        
        except ImportError:
            logger.warning("WebSearchTool not available for web search")
            findings.append({
                "source": "web_search_unavailable",
                "content": "Web search tools not available",
                "relevance": 0.0
            })
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            findings.append({
                "source": "web_search_error",
                "content": f"Web search failed: {str(e)}",
                "relevance": 0.0
            })
        
        return findings
    
    async def _execute_ai_analysis(self, topic: str, findings: List[Dict[str, Any]], depth: str) -> Dict[str, Any]:
        """Execute AI-powered analysis of findings"""
        try:
            # Import LLM router if available
            from ..llm_router import LLMRouter
            
            llm_router = LLMRouter()
            
            # Prepare findings for analysis
            findings_text = self._prepare_findings_for_ai(findings)
            
            # Create analysis prompt based on depth
            if depth == "expert":
                prompt = f"""Perform an expert-level analysis of the research findings about "{topic}".
                
Research Findings:
{findings_text}

Provide a comprehensive analysis including:
1. Key technical insights and implications
2. Patterns and connections between findings
3. Gaps in current knowledge
4. Recommendations for further investigation
5. Practical applications and use cases
6. Potential challenges and limitations

Format as structured JSON with clear sections."""
            else:
                prompt = f"""Analyze the research findings about "{topic}" and provide insights.
                
Research Findings:
{findings_text}

Provide:
1. Key insights from the findings
2. Main themes and patterns
3. Practical implications
4. Summary recommendations

Keep the analysis concise but comprehensive."""
            
            # Generate AI insights
            response = await llm_router.generate(prompt)
            ai_content = response.get("response", "Analysis failed")
            
            return {
                "analysis_type": f"{depth}_ai_analysis",
                "topic": topic,
                "findings_analyzed": len(findings),
                "insights": ai_content,
                "model_used": response.get("model", "unknown"),
                "confidence": 0.8 if len(findings) > 3 else 0.6,
                "generated_at": datetime.now().isoformat()
            }
            
        except ImportError:
            logger.warning("LLMRouter not available for AI analysis")
            return {
                "analysis_type": "ai_analysis_unavailable",
                "topic": topic,
                "error": "AI analysis tools not available",
                "confidence": 0.0
            }
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "analysis_type": "ai_analysis_error",
                "topic": topic,
                "error": str(e),
                "confidence": 0.0
            }
    
    async def _execute_code_analysis(self, topic: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute code analysis for patterns related to topic"""
        findings = []
        analysis_type = parameters.get("analysis_type", "patterns")
        focus_areas = parameters.get("focus_areas", [topic])
        
        try:
            # Analyze Python files in the project
            python_files = list(self.project_root.rglob("*.py"))
            
            for file_path in python_files[:20]:  # Limit to first 20 files
                try:
                    file_analysis = await self._analyze_python_file(file_path, focus_areas)
                    if file_analysis:
                        findings.extend(file_analysis)
                except Exception as e:
                    logger.debug(f"Failed to analyze {file_path}: {e}")
                    continue
            
            # Add summary of code analysis
            if findings:
                findings.append({
                    "source": "code_analysis_summary",
                    "type": "analysis_summary",
                    "content": f"Analyzed {len(python_files)} Python files, found {len(findings)} relevant patterns",
                    "patterns_found": len([f for f in findings if f.get("type") == "code_pattern"]),
                    "relevance": 0.7
                })
        
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            findings.append({
                "source": "code_analysis_error",
                "content": f"Code analysis failed: {str(e)}",
                "relevance": 0.0
            })
        
        return findings
    
    async def _generate_research_summary(self, research_results: Dict[str, Any]) -> str:
        """Generate a comprehensive research summary"""
        topic = research_results.get("topic", "Unknown")
        findings_count = len(research_results.get("findings", []))
        confidence = research_results.get("confidence_score", 0)
        
        summary_parts = [
            f"Research Summary: {topic}",
            f"Confidence Level: {confidence}%",
            f"Sources Analyzed: {findings_count} findings from {len(research_results.get('sources_used', []))} source types"
        ]
        
        # Add key findings
        findings = research_results.get("findings", [])
        if findings:
            top_findings = sorted(findings, key=lambda x: x.get("relevance", 0), reverse=True)[:3]
            summary_parts.append("\nKey Findings:")
            for i, finding in enumerate(top_findings, 1):
                source = finding.get("source", "Unknown")
                content = finding.get("content", finding.get("snippet", "No content"))[:200]
                summary_parts.append(f"{i}. [{source}] {content}...")
        
        # Add AI insights if available
        ai_insights = research_results.get("ai_insights")
        if ai_insights and isinstance(ai_insights, dict):
            insights_content = ai_insights.get("insights", "")
            if insights_content:
                summary_parts.append(f"\nAI Analysis: {insights_content[:300]}...")
        
        # Add research plan summary
        plan = research_results.get("research_plan", [])
        if plan:
            completed_steps = len([step for step in plan if step.get("completed", True)])
            summary_parts.append(f"\nResearch Plan: {completed_steps}/{len(plan)} steps completed")
        
        return "\n".join(summary_parts)
    
    async def _search_project_docs(self, topic: str, depth: str) -> List[Dict[str, Any]]:
        """Search project documentation files"""
        findings = []
        doc_patterns = ["*.md", "*.rst", "*.txt"]
        
        try:
            doc_files = []
            for pattern in doc_patterns:
                doc_files.extend(self.project_root.rglob(pattern))
            
            # Prioritize important documentation files
            priority_files = [f for f in doc_files if any(name in f.name.lower() for name in ["readme", "setup", "install", "guide", "docs"])]
            other_files = [f for f in doc_files if f not in priority_files]
            
            # Process priority files first
            for doc_file in (priority_files + other_files)[:10]:  # Limit to 10 files
                try:
                    async with aiofiles.open(doc_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    
                    relevance = self._calculate_text_relevance(topic, content)
                    if relevance > 0.1:  # Only include relevant content
                        findings.append({
                            "source": str(doc_file.relative_to(self.project_root)),
                            "type": "documentation",
                            "content": content[:1000] + "..." if len(content) > 1000 else content,
                            "relevance": relevance,
                            "file_size": len(content),
                            "last_modified": datetime.fromtimestamp(doc_file.stat().st_mtime).isoformat()
                        })
                
                except Exception as e:
                    logger.debug(f"Failed to read {doc_file}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Documentation search failed: {e}")
        
        return findings
    
    async def _search_codebase(self, topic: str, depth: str) -> List[Dict[str, Any]]:
        """Search codebase for topic-related content"""
        findings = []
        
        try:
            python_files = list(self.project_root.rglob("*.py"))
            
            for py_file in python_files[:15]:  # Limit to 15 files
                try:
                    async with aiofiles.open(py_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    
                    relevance = self._calculate_text_relevance(topic, content)
                    if relevance > 0.2:  # Higher threshold for code files
                        # Extract relevant code snippets
                        snippets = self._extract_relevant_code_snippets(content, topic)
                        
                        findings.append({
                            "source": str(py_file.relative_to(self.project_root)),
                            "type": "source_code",
                            "content": "\n".join(snippets[:3]) if snippets else content[:500],
                            "relevance": relevance,
                            "snippets_found": len(snippets),
                            "file_lines": len(content.splitlines())
                        })
                
                except Exception as e:
                    logger.debug(f"Failed to read {py_file}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Codebase search failed: {e}")
        
        return findings
    
    async def _search_config_files(self, topic: str) -> List[Dict[str, Any]]:
        """Search configuration files"""
        findings = []
        config_patterns = ["*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg", "*.env*"]
        
        try:
            config_files = []
            for pattern in config_patterns:
                config_files.extend(self.project_root.rglob(pattern))
            
            for config_file in config_files[:8]:  # Limit to 8 config files
                try:
                    async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                    
                    relevance = self._calculate_text_relevance(topic, content)
                    if relevance > 0.15:
                        findings.append({
                            "source": str(config_file.relative_to(self.project_root)),
                            "type": "configuration",
                            "content": content[:800] + "..." if len(content) > 800 else content,
                            "relevance": relevance,
                            "config_type": config_file.suffix
                        })
                
                except Exception as e:
                    logger.debug(f"Failed to read config {config_file}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Configuration search failed: {e}")
        
        return findings
    
    def _get_kairos_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """Get Kairos-specific knowledge about the topic"""
        kairos_knowledge = {
            "context engineering": {
                "content": "Kairos implements advanced context engineering through layered memory systems, maintaining project consistency and long-term memory across development sessions.",
                "relevance": 0.95,
                "type": "core_concept"
            },
            "agent architecture": {
                "content": "Multi-agent system with specialized roles: ResearchAgent (information gathering), ExecutionAgent (task execution), GuardianAgent (output validation), LinkAgent (relationship mapping), and RetrievalAgent (context retrieval).",
                "relevance": 0.9,
                "type": "architecture"
            },
            "memory management": {
                "content": "Hybrid memory system combining Neo4j knowledge graphs for structured relationships with Qdrant vector storage for semantic search and context retrieval.",
                "relevance": 0.9,
                "type": "technical_implementation"
            },
            "model routing": {
                "content": "Intelligent LLM routing system that selects optimal models based on task type, performance metrics, and cost considerations. Supports Ollama local models, Gemini, OpenRouter, and custom model integration.",
                "relevance": 0.85,
                "type": "ai_integration"
            },
            "mcp protocol": {
                "content": "Model Context Protocol implementation enabling structured communication between system and LLMs, providing enhanced context awareness and tool usage capabilities.",
                "relevance": 0.9,
                "type": "protocol"
            }
        }
        
        findings = []
        topic_lower = topic.lower()
        
        for key, knowledge in kairos_knowledge.items():
            if any(word in key for word in topic_lower.split()) or any(word in topic_lower for word in key.split()):
                findings.append({
                    "source": "kairos_knowledge_base",
                    "type": knowledge["type"],
                    "content": knowledge["content"],
                    "relevance": knowledge["relevance"],
                    "topic_match": key
                })
        
        return findings
    
    async def _analyze_python_file(self, file_path: Path, focus_areas: List[str]) -> List[Dict[str, Any]]:
        """Analyze a Python file for patterns related to focus areas"""
        findings = []
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Parse AST for structural analysis
            tree = ast.parse(content)
            
            # Find relevant classes, functions, and imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if any(area.lower() in node.name.lower() for area in focus_areas):
                        findings.append({
                            "source": str(file_path.relative_to(self.project_root)),
                            "type": "code_pattern",
                            "pattern_type": "class",
                            "name": node.name,
                            "content": f"Class {node.name} found",
                            "line": getattr(node, 'lineno', 0),
                            "relevance": 0.8
                        })
                
                elif isinstance(node, ast.FunctionDef):
                    if any(area.lower() in node.name.lower() for area in focus_areas):
                        findings.append({
                            "source": str(file_path.relative_to(self.project_root)),
                            "type": "code_pattern",
                            "pattern_type": "function",
                            "name": node.name,
                            "content": f"Function {node.name} found",
                            "line": getattr(node, 'lineno', 0),
                            "relevance": 0.7
                        })
        
        except SyntaxError:
            # File might not be valid Python
            pass
        except Exception as e:
            logger.debug(f"AST analysis failed for {file_path}: {e}")
        
        return findings
    
    def _calculate_text_relevance(self, topic: str, text: str) -> float:
        """Calculate relevance score between topic and text"""
        if not topic or not text:
            return 0.0
        
        topic_words = set(topic.lower().split())
        text_words = set(text.lower().split())
        
        # Exact matches
        exact_matches = len(topic_words.intersection(text_words))
        if exact_matches == 0:
            return 0.0
        
        # Partial matches
        partial_matches = 0
        for topic_word in topic_words:
            for text_word in text_words:
                if topic_word in text_word or text_word in topic_word:
                    partial_matches += 0.5
        
        # Calculate relevance score
        total_score = exact_matches + partial_matches
        max_possible = len(topic_words)
        
        relevance = min(total_score / max_possible, 1.0)
        return relevance
    
    def _extract_relevant_code_snippets(self, content: str, topic: str) -> List[str]:
        """Extract code snippets relevant to the topic"""
        snippets = []
        lines = content.splitlines()
        topic_words = set(topic.lower().split())
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_lower = line.lower()
            
            # Check if line contains topic-related keywords
            if any(word in line_lower for word in topic_words):
                # Extract surrounding context (3 lines before and after)
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                snippet = "\n".join(lines[start:end])
                snippets.append(f"Line {i+1}: {snippet}")
                i = end  # Skip processed lines
            else:
                i += 1
        
        return snippets[:5]  # Return top 5 snippets
    
    def _prepare_findings_for_ai(self, findings: List[Dict[str, Any]]) -> str:
        """Prepare findings text for AI analysis"""
        if not findings:
            return "No findings available for analysis."
        
        findings_text = []
        
        for i, finding in enumerate(findings[:10], 1):  # Limit to top 10 findings
            source = finding.get("source", "Unknown")
            content = finding.get("content", "No content")
            relevance = finding.get("relevance", 0.0)
            
            findings_text.append(f"{i}. Source: {source} (Relevance: {relevance:.2f})")
            findings_text.append(f"   Content: {content[:500]}...")
            findings_text.append("")
        
        return "\n".join(findings_text)


# Global utilities instance
mcp_utils = MCPUtilities()
