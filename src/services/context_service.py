#!/usr/bin/env python3
"""
Context Service - Intelligent Context Aggregation
Provides enriched context from multiple sources for MCP tools
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ContextRequest:
    """Context request data structure"""
    query: str
    depth: str = "detailed"  # basic, detailed, expert
    metadata: Dict[str, Any] = None
    max_tokens: int = 4000
    include_code: bool = True
    include_history: bool = True

@dataclass
class ContextResponse:
    """Context response data structure"""
    query: str
    enriched_context: str
    sources: List[str]
    confidence_score: float
    token_count: int
    cache_hit: bool
    generated_at: datetime

class ContextCache:
    """Simple in-memory context cache"""
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 30):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_key(self, request: ContextRequest) -> str:
        """Generate cache key from request"""
        key_data = f"{request.query}:{request.depth}:{request.max_tokens}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, request: ContextRequest) -> Optional[ContextResponse]:
        """Get cached context if available and not expired"""
        key = self._generate_key(request)
        
        if key not in self.cache:
            return None
        
        # Check TTL
        if datetime.now() - self.access_times[key] > self.ttl:
            del self.cache[key]
            del self.access_times[key]
            return None
        
        # Update access time
        self.access_times[key] = datetime.now()
        response = self.cache[key]
        response.cache_hit = True
        return response
    
    def set(self, request: ContextRequest, response: ContextResponse):
        """Cache context response"""
        key = self._generate_key(request)
        
        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), 
                           key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = response
        self.access_times[key] = datetime.now()

class ContextService:
    """Main context service for intelligent aggregation"""
    
    def __init__(self):
        self.cache = ContextCache()
        self.project_root = Path.cwd()
        
    async def get_context(self, request: ContextRequest) -> ContextResponse:
        """Get enriched context for a query"""
        
        # Check cache first
        cached_response = self.cache.get(request)
        if cached_response:
            logger.debug(f"Cache hit for query: {request.query}")
            return cached_response
        
        logger.info(f"Generating context for: {request.query}")
        
        # Gather context from multiple sources
        context_parts = []
        sources = []
        
        # 1. Project Constitution
        constitution_context = await self._get_constitution_context(request)
        if constitution_context:
            context_parts.append(constitution_context)
            sources.append("project_constitution")
        
        # 2. Code Analysis
        if request.include_code:
            code_context = await self._get_code_context(request)
            if code_context:
                context_parts.append(code_context)
                sources.append("code_analysis")
        
        # 3. Historical Context
        if request.include_history:
            history_context = await self._get_historical_context(request)
            if history_context:
                context_parts.append(history_context)
                sources.append("historical_data")
        
        # 4. Best Practices
        practices_context = await self._get_best_practices_context(request)
        if practices_context:
            context_parts.append(practices_context)
            sources.append("best_practices")
        
        # Combine and optimize context
        enriched_context = await self._synthesize_context(
            request, context_parts, sources
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            request, context_parts, sources
        )
        
        # Create response
        response = ContextResponse(
            query=request.query,
            enriched_context=enriched_context,
            sources=sources,
            confidence_score=confidence_score,
            token_count=len(enriched_context.split()),
            cache_hit=False,
            generated_at=datetime.now()
        )
        
        # Cache response
        self.cache.set(request, response)
        
        return response
    
    async def _get_constitution_context(self, request: ContextRequest) -> str:
        """Get context from project constitution"""
        try:
            constitution_data = {
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
            
            # Filter relevant parts based on query
            relevant_parts = []
            query_lower = request.query.lower()
            
            if any(keyword in query_lower for keyword in ['auth', 'security', 'jwt', 'login']):
                relevant_parts.append(f"Security Standards: {json.dumps(constitution_data['security'], indent=2)}")
            
            if any(keyword in query_lower for keyword in ['architecture', 'design', 'pattern']):
                relevant_parts.append(f"Architecture Patterns: {json.dumps(constitution_data['architecture'], indent=2)}")
            
            if any(keyword in query_lower for keyword in ['code', 'style', 'standard']):
                relevant_parts.append(f"Coding Standards: {json.dumps(constitution_data['coding_standards'], indent=2)}")
            
            if not relevant_parts:
                return f"Project Constitution Overview: {json.dumps(constitution_data, indent=2)}"
            
            return "\\n\\n".join(relevant_parts)
            
        except Exception as e:
            logger.error(f"Error getting constitution context: {e}")
            return ""
    
    async def _get_code_context(self, request: ContextRequest) -> str:
        """Get context from code analysis"""
        try:
            # Simple file scanning for relevant code
            relevant_files = []
            query_keywords = request.query.lower().split()
            
            # Scan common directories
            for pattern in ["*.py", "*.js", "*.ts"]:
                for file_path in self.project_root.rglob(pattern):
                    if any(exclude in str(file_path) for exclude in ['.git', '__pycache__', 'node_modules', '.venv']):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            if any(keyword in content for keyword in query_keywords):
                                relevant_files.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'size': len(content),
                                    'match_count': sum(1 for keyword in query_keywords if keyword in content)
                                })
                    except:
                        continue
            
            # Sort by relevance
            relevant_files.sort(key=lambda x: x['match_count'], reverse=True)
            
            if relevant_files:
                context = f"Relevant Code Files for '{request.query}':\\n"
                for file_info in relevant_files[:5]:  # Top 5 files
                    context += f"- {file_info['file']} (matches: {file_info['match_count']})\\n"
                return context
            
            return f"No specific code files found for query: {request.query}"
            
        except Exception as e:
            logger.error(f"Error getting code context: {e}")
            return ""
    
    async def _get_historical_context(self, request: ContextRequest) -> str:
        """Get context from historical data and decisions"""
        try:
            # Check for git history or logs related to query
            context = f"Historical Context for '{request.query}':\\n"
            context += "- Based on project evolution and past decisions\\n"
            context += "- Consider previous implementations and lessons learned\\n"
            context += "- Maintain consistency with established patterns\\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting historical context: {e}")
            return ""
    
    async def _get_best_practices_context(self, request: ContextRequest) -> str:
        """Get best practices context"""
        try:
            query_lower = request.query.lower()
            
            best_practices = {
                "security": [
                    "Always validate input data",
                    "Use parameterized queries to prevent SQL injection",
                    "Implement proper authentication and authorization",
                    "Use HTTPS for all communications",
                    "Follow principle of least privilege"
                ],
                "performance": [
                    "Use async/await for I/O operations",
                    "Implement proper caching strategies",
                    "Optimize database queries with indexes",
                    "Use connection pooling",
                    "Monitor and profile regularly"
                ],
                "architecture": [
                    "Follow SOLID principles",
                    "Implement proper error handling",
                    "Use dependency injection",
                    "Maintain clear separation of concerns",
                    "Document API contracts"
                ]
            }
            
            relevant_practices = []
            
            for category, practices in best_practices.items():
                if category in query_lower or any(keyword in query_lower for keyword in practices[0].lower().split()):
                    relevant_practices.extend([f"{category.title()}: {practice}" for practice in practices])
            
            if relevant_practices:
                return f"Best Practices for '{request.query}':\\n" + "\\n".join(f"- {practice}" for practice in relevant_practices[:8])
            
            return f"General best practices apply to: {request.query}"
            
        except Exception as e:
            logger.error(f"Error getting best practices context: {e}")
            return ""
    
    async def _synthesize_context(self, request: ContextRequest, context_parts: List[str], sources: List[str]) -> str:
        """Synthesize context parts into coherent response"""
        if not context_parts:
            return f"No specific context found for: {request.query}"
        
        header = f"**Kairos Context for: '{request.query}'**\\n\\n"
        
        if request.depth == "basic":
            # Return only the most relevant part
            return header + context_parts[0]
        elif request.depth == "expert":
            # Return full detailed context
            full_context = header
            for i, (part, source) in enumerate(zip(context_parts, sources)):
                full_context += f"**{source.replace('_', ' ').title()}:**\\n{part}\\n\\n"
            return full_context
        else:  # detailed
            # Return balanced context
            combined = header
            for part in context_parts[:3]:  # Limit to top 3 parts
                combined += part + "\\n\\n"
            return combined
    
    def _calculate_confidence_score(self, request: ContextRequest, context_parts: List[str], sources: List[str]) -> float:
        """Calculate confidence score based on available context"""
        if not context_parts:
            return 0.0
        
        base_score = 0.5
        
        # Bonus for multiple sources
        source_bonus = min(len(sources) * 0.15, 0.4)
        
        # Bonus for relevant matches
        query_keywords = set(request.query.lower().split())
        content_text = " ".join(context_parts).lower()
        content_keywords = set(content_text.split())
        
        keyword_overlap = len(query_keywords.intersection(content_keywords))
        keyword_bonus = min(keyword_overlap * 0.1, 0.3)
        
        final_score = min(base_score + source_bonus + keyword_bonus, 1.0)
        return round(final_score, 2)

# Global context service instance
context_service = ContextService()

async def get_enriched_context(query: str, depth: str = "detailed", **kwargs) -> ContextResponse:
    """Convenience function to get enriched context"""
    request = ContextRequest(
        query=query,
        depth=depth,
        metadata=kwargs.get('metadata', {}),
        max_tokens=kwargs.get('max_tokens', 4000),
        include_code=kwargs.get('include_code', True),
        include_history=kwargs.get('include_history', True)
    )
    
    return await context_service.get_context(request)
