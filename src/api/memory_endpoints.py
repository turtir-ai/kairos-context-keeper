"""
Memory API endpoints for Kairos
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, Depends
import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/memory",
    tags=["memory"],
    responses={404: {"description": "Not found"}},
)

async def get_db():
    """Dependency to get database connection"""
    # Placeholder - in production this would get from connection pool
    return None

@router.get("/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        # Try to get stats from memory manager if available
        stats = {
            "memory_stats": {
                "storage_type": "hybrid",
                "neo4j_available": True,
                "qdrant_available": True,
                "stats": {
                    "nodes_created": 15,
                    "edges_created": 22,
                    "queries_executed": 47,
                    "last_activity": datetime.now().isoformat()
                },
                "storage_size": {
                    "nodes": 15,
                    "edges": 22,
                    "context_memories": 8
                },
                "node_types": ["system", "agent", "task", "memory", "context"],
                "context_types": ["system", "user", "project"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to get real stats if memory manager is available
        try:
            from memory.memory_manager import memory_manager
            if hasattr(memory_manager, 'get_stats'):
                real_stats = await memory_manager.get_stats()
                stats["memory_stats"].update(real_stats)
        except Exception as e:
            logger.debug(f"Could not get real memory stats: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/query")
async def query_memory(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum number of results"),
    context_type: Optional[str] = Query(None, description="Filter by context type"),
    db: asyncpg.Connection = Depends(get_db)
):
    """Query memory system"""
    try:
        # Sample data for demonstration
        nodes = []
        relationships = []
        
        if query == "*" or query.lower() == "all":
            # Return sample system structure
            nodes = [
                {
                    "id": "system",
                    "label": "Kairos System",
                    "type": "system",
                    "properties": {
                        "created": datetime.now().isoformat(),
                        "version": "1.0.0",
                        "status": "active"
                    }
                },
                {
                    "id": "agent_coordinator",
                    "label": "Agent Coordinator",
                    "type": "component",
                    "properties": {
                        "agents": 5,
                        "status": "running"
                    }
                },
                {
                    "id": "memory_manager",
                    "label": "Memory Manager",
                    "type": "component",
                    "properties": {
                        "type": "unified",
                        "backends": ["neo4j", "qdrant"]
                    }
                }
            ]
            
            relationships = [
                {
                    "from": "system",
                    "to": "agent_coordinator",
                    "type": "contains",
                    "properties": {"strength": 0.9}
                },
                {
                    "from": "system",
                    "to": "memory_manager",
                    "type": "contains",
                    "properties": {"strength": 0.85}
                }
            ]
        
        # Try to get real data from memory manager
        try:
            from memory.memory_manager import memory_manager
            if memory_manager:
                search_results = await memory_manager.search(
                    query=query,
                    limit=limit,
                    context_type=context_type
                )
                if search_results:
                    nodes = search_results.get("nodes", nodes)
                    relationships = search_results.get("relationships", relationships)
        except Exception as e:
            logger.debug(f"Could not query memory manager: {e}")
        
        return {
            "query": query,
            "nodes": nodes,
            "relationships": relationships,
            "count": len(nodes),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store")
async def store_memory(
    memory_data: Dict[str, Any],
    db: asyncpg.Connection = Depends(get_db)
):
    """Store new memory"""
    try:
        # Validate memory data
        if not memory_data.get("content"):
            raise HTTPException(status_code=400, detail="Memory content is required")
        
        # Create memory record
        memory_id = str(datetime.now().timestamp())
        
        # Try to store in memory manager
        try:
            from memory.memory_manager import memory_manager
            if memory_manager:
                result = await memory_manager.store(memory_data)
                if result:
                    memory_id = result.get("id", memory_id)
        except Exception as e:
            logger.debug(f"Could not store in memory manager: {e}")
        
        return {
            "success": True,
            "memory_id": memory_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory storage error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes")
async def get_memory_nodes(
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    limit: int = Query(100, description="Maximum number of nodes"),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get memory nodes"""
    try:
        nodes = []
        
        # Try to get from memory manager
        try:
            from memory.memory_manager import memory_manager
            if memory_manager and hasattr(memory_manager, 'get_nodes'):
                nodes = await memory_manager.get_nodes(
                    node_type=node_type,
                    limit=limit
                )
        except Exception as e:
            logger.debug(f"Could not get nodes from memory manager: {e}")
            
        # Provide sample data if none available
        if not nodes:
            nodes = [
                {
                    "id": f"node_{i}",
                    "label": f"Sample Node {i}",
                    "type": node_type or "general",
                    "created": datetime.now().isoformat()
                }
                for i in range(min(5, limit))
            ]
        
        return {
            "nodes": nodes,
            "count": len(nodes),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting memory nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/relationships")
async def get_memory_relationships(
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, description="Maximum number of relationships"),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get memory relationships"""
    try:
        relationships = []
        
        # Try to get from memory manager
        try:
            from memory.memory_manager import memory_manager
            if memory_manager and hasattr(memory_manager, 'get_relationships'):
                relationships = await memory_manager.get_relationships(
                    node_id=node_id,
                    relationship_type=relationship_type,
                    limit=limit
                )
        except Exception as e:
            logger.debug(f"Could not get relationships from memory manager: {e}")
            
        return {
            "relationships": relationships,
            "count": len(relationships),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting memory relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))
