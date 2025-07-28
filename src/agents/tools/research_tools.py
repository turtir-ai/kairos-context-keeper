"""
Research Tools for External Data Gathering
"""

import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
import logging
from bs4 import BeautifulSoup
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Tool for web searching and scraping"""
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def search_wikipedia(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search Wikipedia for a topic"""
        results = []
        
        try:
            # Wikipedia API endpoint
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": limit
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("query", {}).get("search", []):
                        results.append({
                            "source": "Wikipedia",
                            "title": item.get("title"),
                            "snippet": BeautifulSoup(item.get("snippet", ""), "html.parser").text,
                            "url": f"https://en.wikipedia.org/wiki/{item.get('title').replace(' ', '_')}",
                            "timestamp": datetime.now().isoformat()
                        })
                        
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
            
        return results
        
    async def search_github(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search GitHub repositories"""
        results = []
        
        try:
            # GitHub API endpoint (no auth for basic search)
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": limit
            }
            
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for repo in data.get("items", []):
                        results.append({
                            "source": "GitHub",
                            "name": repo.get("full_name"),
                            "description": repo.get("description"),
                            "stars": repo.get("stargazers_count"),
                            "language": repo.get("language"),
                            "url": repo.get("html_url"),
                            "topics": repo.get("topics", []),
                            "timestamp": datetime.now().isoformat()
                        })
                        
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            
        return results
        
    async def fetch_webpage_content(self, url: str) -> Optional[str]:
        """Fetch and extract text content from a webpage"""
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    # Get text
                    text = soup.get_text()
                    
                    # Clean up text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    return text[:2000]  # Limit to first 2000 chars
                    
        except Exception as e:
            logger.error(f"Failed to fetch webpage {url}: {e}")
            
        return None


class LocalKnowledgeTool:
    """Tool for searching local project knowledge"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        
    async def search_documentation(self, query: str) -> List[Dict[str, Any]]:
        """Search project documentation"""
        results = []
        doc_files = [
            ".kiro/steering.md",
            ".kiro/specs.md", 
            "README.md",
            "SETUP.md",
            "docs/*.md"
        ]
        
        # Implementation for searching local docs
        # This is a placeholder - would need actual file searching logic
        
        return results
        
    async def analyze_codebase(self, query: str) -> Dict[str, Any]:
        """Analyze codebase for specific patterns or concepts"""
        analysis = {
            "query": query,
            "files_analyzed": 0,
            "matches": [],
            "patterns": []
        }
        
        # Implementation for code analysis
        # This is a placeholder - would use AST parsing, regex, etc.
        
        return analysis


class AIAnalysisTool:
    """Tool for AI-powered analysis and synthesis"""
    
    def __init__(self, llm_router=None):
        self.llm_router = llm_router
        
    async def synthesize_findings(self, findings: List[Dict[str, Any]], query: str) -> str:
        """Synthesize multiple findings into a coherent summary"""
        if not self.llm_router:
            return "AI synthesis not available"
            
        # Prepare findings text
        findings_text = "\n\n".join([
            f"Source: {f.get('source', 'Unknown')}\n{f.get('snippet', f.get('description', ''))}"
            for f in findings[:5]  # Limit to top 5
        ])
        
        prompt = f"""Synthesize these research findings about "{query}" into a clear, concise summary:

{findings_text}

Provide:
1. Key insights
2. Common themes
3. Practical implications
4. Recommended next steps
"""
        
        try:
            response = await self.llm_router.generate(prompt)
            return response.get("response", "Synthesis failed")
        except Exception as e:
            logger.error(f"AI synthesis failed: {e}")
            return f"Synthesis error: {str(e)}"
            
    async def extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        if not self.llm_router:
            return []
            
        prompt = f"""Extract 5-10 key technical concepts from this text. 
Return only a comma-separated list of concepts, nothing else:

{text[:1000]}
"""
        
        try:
            response = await self.llm_router.generate(prompt)
            concepts = response.get("response", "").split(",")
            return [c.strip() for c in concepts if c.strip()]
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            return []
