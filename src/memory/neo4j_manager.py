#!/usr/bin/env python3
"""
Neo4j Manager
Manages connections and operations with Neo4j Knowledge Graph database
"""

import logging
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class Neo4jManager:
    """Manager for Neo4j database operations"""
    
    def __init__(self):
        self.driver = None
        self.connected = False
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup Neo4j connection"""
        try:
            # Try to import neo4j driver
            from neo4j import GraphDatabase
            
            # Get connection details from environment or defaults
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            username = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'password')
            
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
                
            self.connected = True
            logger.info("Successfully connected to Neo4j database")
            
        except ImportError:
            logger.warning("Neo4j driver not installed. Running in offline mode.")
            self.connected = False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Neo4j"""
        return self.connected and self.driver is not None
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query"""
        if not self.is_connected():
            # Only log the first few times to avoid spam
            if not hasattr(self, '_log_count'):
                self._log_count = 0
            if self._log_count < 1:
                logger.debug("Neo4j not connected. Queries will be ignored.")
                self._log_count += 1
            return []
        
        try:
            with self.driver.session() as session:
                parameters = parameters or {}
                result = session.run(query, parameters)
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Error executing Neo4j query: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Parameters: {parameters}")
            return []
    
    def execute_write_query(self, query: str, parameters: Dict[str, Any] = None) -> bool:
        """Execute a write query (CREATE, MERGE, DELETE, etc.)"""
        if not self.connected or not self.driver:
            logger.warning("Neo4j not connected. Write query ignored.")
            return False
        
        try:
            with self.driver.session() as session:
                parameters = parameters or {}
                session.run(query, parameters)
                return True
                
        except Exception as e:
            logger.error(f"Error executing Neo4j write query: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Parameters: {parameters}")
            return False
    
    def test_connection(self) -> bool:
        """Test if Neo4j connection is working"""
        if not self.connected:
            return False
        
        try:
            result = self.execute_query("RETURN 1 as test")
            return len(result) > 0
        except:
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the Neo4j database"""
        if not self.connected:
            return {
                "connected": False,
                "error": "Neo4j not connected"
            }
        
        try:
            # Get basic database info
            stats_query = """
            CALL db.stats.retrieve('GRAPH COUNTS') YIELD data
            RETURN data
            """
            
            # Fallback to simple node/relationship counts
            node_count_query = "MATCH (n) RETURN count(n) as count"
            rel_count_query = "MATCH ()-[r]->() RETURN count(r) as count"
            
            node_result = self.execute_query(node_count_query)
            rel_result = self.execute_query(rel_count_query)
            
            return {
                "connected": True,
                "nodes": node_result[0]['count'] if node_result else 0,
                "relationships": rel_result[0]['count'] if rel_result else 0,
                "driver_version": "4.x"  # Placeholder
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {
                "connected": True,
                "error": str(e)
            }
    
    def clear_database(self) -> bool:
        """Clear all data from the database (use with caution!)"""
        if not self.connected:
            logger.warning("Neo4j not connected. Cannot clear database.")
            return False
        
        try:
            clear_query = "MATCH (n) DETACH DELETE n"
            return self.execute_write_query(clear_query)
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """Create recommended indexes for code analysis"""
        if not self.connected:
            logger.warning("Neo4j not connected. Cannot create indexes.")
            return False
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.file_path)",
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:CodeNode) ON (n.type)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Module) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Function) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Class) ON (n.name)"
        ]
        
        success = True
        for index_query in indexes:
            if not self.execute_write_query(index_query):
                success = False
                logger.error(f"Failed to create index: {index_query}")
            else:
                logger.info(f"Created index: {index_query}")
        
        return success
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.connected = False
            logger.info("Neo4j connection closed")

# Global manager instance
neo4j_manager = Neo4jManager()
