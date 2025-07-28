#!/usr/bin/env python3
"""
AST to Graph Converter
Converts parsed AST nodes and relationships to Neo4j Cypher queries
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime
import json

from .neo4j_manager import neo4j_manager

# Handle imports for different contexts
try:
    from ..core.code_parser import CodeNode, CodeRelationship, NodeType
except ImportError:
    try:
        from core.code_parser import CodeNode, CodeRelationship, NodeType
    except ImportError:
        # Define minimal classes for testing
        from enum import Enum
        from dataclasses import dataclass
        from typing import Dict, Any
        
        class NodeType(Enum):
            MODULE = "module"
            CLASS = "class"
            FUNCTION = "function"
            IMPORT = "import"
        
        @dataclass
        class CodeNode:
            id: str
            type: NodeType
            name: str
            file_path: str
            start_line: int
            end_line: int
            start_char: int
            end_char: int
            content: str
            metadata: Dict[str, Any] = None
        
        @dataclass
        class CodeRelationship:
            id: str
            source_id: str
            target_id: str
            relationship_type: str
            metadata: Dict[str, Any] = None

logger = logging.getLogger(__name__)

class ASTConverter:
    """Converts AST data to Neo4j knowledge graph"""
    
    def __init__(self):
        self.neo4j = neo4j_manager
    
    def convert_nodes_to_cypher(self, nodes: List[CodeNode]) -> List[str]:
        """Convert CodeNode objects to Cypher CREATE statements"""
        cypher_statements = []
        
        for node in nodes:
            # Escape strings for Cypher
            escaped_content = self._escape_for_cypher(node.content)
            escaped_name = self._escape_for_cypher(node.name)
            escaped_path = self._escape_for_cypher(node.file_path)
            
            # Create node properties
            properties = {
                'id': node.id,
                'name': escaped_name,
                'type': node.type.value,
                'file_path': escaped_path,
                'start_line': node.start_line,
                'end_line': node.end_line,
                'start_char': node.start_char,
                'end_char': node.end_char,
                'content': escaped_content,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Add metadata
            if node.metadata:
                for key, value in node.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        properties[f'meta_{key}'] = value
                    elif isinstance(value, list):
                        # Convert lists to JSON strings
                        properties[f'meta_{key}'] = json.dumps(value)
            
            # Build property string using proper escaping
            props_list = []
            for k, v in properties.items():
                props_list.append(f'{k}: {self._prepare_property_value(v)}')
            props_str = ', '.join(props_list)
            
            # Create Cypher statement
            cypher = f"""
            MERGE (n:CodeNode {{id: "{node.id}"}})
            SET n += {{{props_str}}}
            SET n:Code:{node.type.value.capitalize()}
            """
            
            cypher_statements.append(cypher.strip())
        
        return cypher_statements
    
    def convert_relationships_to_cypher(self, relationships: List[CodeRelationship]) -> List[str]:
        """Convert CodeRelationship objects to Cypher CREATE statements"""
        cypher_statements = []
        
        for rel in relationships:
            # Create relationship properties
            properties = {
                'id': rel.id,
                'type': rel.relationship_type,
                'created_at': datetime.now().isoformat()
            }
            
            # Add metadata
            if rel.metadata:
                for key, value in rel.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        properties[f'meta_{key}'] = value
                    elif isinstance(value, list):
                        properties[f'meta_{key}'] = json.dumps(value)
            
            # Build property string using proper escaping
            props_list = []
            for k, v in properties.items():
                props_list.append(f'{k}: {self._prepare_property_value(v)}')
            props_str = ', '.join(props_list)
            
            # Create Cypher statement
            cypher = f"""
            MATCH (source:CodeNode {{id: "{rel.source_id}"}})
            MATCH (target:CodeNode {{id: "{rel.target_id}"}})
            MERGE (source)-[r:{rel.relationship_type} {{id: "{rel.id}"}}]->(target)
            SET r += {{{props_str}}}
            """
            
            cypher_statements.append(cypher.strip())
        
        return cypher_statements
    
    def sync_to_neo4j(self, nodes: List[CodeNode], relationships: List[CodeRelationship]) -> bool:
        """Synchronize nodes and relationships to Neo4j"""
        try:
            logger.info(f"Syncing {len(nodes)} nodes and {len(relationships)} relationships to Neo4j")
            
            # Convert to Cypher statements
            node_queries = self.convert_nodes_to_cypher(nodes)
            rel_queries = self.convert_relationships_to_cypher(relationships)
            
            # Execute node creation queries
            for query in node_queries:
                try:
                    self.neo4j.execute_query(query)
                except Exception as e:
                    logger.error(f"Error executing node query: {e}")
                    logger.debug(f"Failed query: {query}")
            
            # Execute relationship creation queries
            for query in rel_queries:
                try:
                    self.neo4j.execute_query(query)
                except Exception as e:
                    logger.error(f"Error executing relationship query: {e}")
                    logger.debug(f"Failed query: {query}")
            
            logger.info("Successfully synced AST data to Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Neo4j: {e}")
            return False
    
    def update_node(self, node: CodeNode) -> bool:
        """Update a single node in Neo4j"""
        try:
            queries = self.convert_nodes_to_cypher([node])
            if queries:
                self.neo4j.execute_query(queries[0])
                return True
        except Exception as e:
            logger.error(f"Error updating node {node.id}: {e}")
        return False
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships from Neo4j"""
        try:
            query = f"""
            MATCH (n:CodeNode {{id: "{node_id}"}})
            DETACH DELETE n
            """
            self.neo4j.execute_query(query)
            logger.info(f"Deleted node {node_id} from Neo4j")
            return True
        except Exception as e:
            logger.error(f"Error deleting node {node_id}: {e}")
            return False
    
    def delete_file_nodes(self, file_path: str) -> bool:
        """Delete all nodes associated with a file"""
        try:
            escaped_path = self._escape_for_cypher(file_path)
            query = f"""
            MATCH (n:CodeNode {{file_path: "{escaped_path}"}})
            DETACH DELETE n
            """
            result = self.neo4j.execute_query(query)
            logger.info(f"Deleted nodes for file {file_path} from Neo4j")
            return True
        except Exception as e:
            logger.error(f"Error deleting file nodes for {file_path}: {e}")
            return False
    
    def get_code_analysis_queries(self) -> Dict[str, str]:
        """Get predefined Cypher queries for code analysis"""
        return {
            "dead_code_detection": """
                MATCH (f:Function)
                WHERE NOT ()-[:CALLS]->(f)
                AND f.name <> '__init__'
                AND f.name <> 'main'
                RETURN f.name, f.file_path, f.start_line
                ORDER BY f.file_path, f.start_line
            """,
            
            "circular_dependencies": """
                MATCH path = (m1:Module)-[:IMPORTS*2..10]->(m1)
                WHERE length(path) > 2
                RETURN [n in nodes(path) | n.name] as cycle,
                       length(path) as cycle_length
                ORDER BY cycle_length
            """,
            
            "complex_functions": """
                MATCH (f:Function)
                WHERE f.meta_complexity > 10
                RETURN f.name, f.file_path, f.meta_complexity, f.start_line
                ORDER BY f.meta_complexity DESC
                LIMIT 20
            """,
            
            "impact_analysis": """
                MATCH (f:Function {name: $function_name})<-[:CALLS*1..5]-(caller)
                RETURN DISTINCT caller.name, caller.file_path, caller.type
                ORDER BY caller.file_path
            """,
            
            "module_dependencies": """
                MATCH (m:Module)-[r:IMPORTS]->(imported)
                RETURN m.name as module, 
                       collect(imported.name) as imports,
                       count(r) as import_count
                ORDER BY import_count DESC
            """,
            
            "unused_imports": """
                MATCH (m:Module)-[:IMPORTS]->(i:Import)
                WHERE NOT EXISTS {
                    MATCH (m)-[:HAS_FUNCTION|HAS_CLASS]->(code)
                    WHERE code.content CONTAINS i.name
                }
                RETURN m.name as module, i.name as unused_import, i.file_path
                ORDER BY m.name
            """,
            
            "technical_debt": """
                MATCH (n:CodeNode)
                WHERE n.content CONTAINS 'TODO' 
                   OR n.content CONTAINS 'FIXME'
                   OR n.content CONTAINS 'HACK'
                   OR n.content CONTAINS 'XXX'
                RETURN n.name, n.file_path, n.start_line, n.content
                ORDER BY n.file_path, n.start_line
            """,
            
            "large_files": """
                MATCH (m:Module)
                WHERE m.meta_lines > 500
                RETURN m.name, m.file_path, m.meta_lines, m.meta_size
                ORDER BY m.meta_lines DESC
            """,
            
            "class_hierarchy": """
                MATCH (c:Class)
                OPTIONAL MATCH (c)-[:INHERITS_FROM]->(parent:Class)
                OPTIONAL MATCH (child:Class)-[:INHERITS_FROM]->(c)
                RETURN c.name as class_name,
                       c.file_path,
                       collect(DISTINCT parent.name) as parents,
                       collect(DISTINCT child.name) as children
                ORDER BY c.name
            """,
            
            "function_calls_graph": """
                MATCH path = (caller:Function)-[:CALLS]->(callee:Function)
                RETURN caller.name as caller, 
                       callee.name as callee,
                       caller.file_path as caller_file,
                       callee.file_path as callee_file
                ORDER BY caller.name
            """
        }
    
    def run_analysis_query(self, query_name: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Run a predefined analysis query"""
        queries = self.get_code_analysis_queries()
        
        if query_name not in queries:
            logger.error(f"Unknown analysis query: {query_name}")
            return []
        
        try:
            query = queries[query_name]
            result = self.neo4j.execute_query(query, parameters or {})
            
            # Convert result to list of dictionaries
            if hasattr(result, 'data'):
                return result.data()
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error running analysis query {query_name}: {e}")
            return []
    
    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a code node by its ID"""
        try:
            query = f"""
            MATCH (n:CodeNode {{id: "{node_id}"}})
            RETURN n
            """
            result = self.neo4j.execute_query(query)
            if result and len(result) > 0:
                return dict(result[0]['n'])
            return None
        except Exception as e:
            logger.error(f"Error getting node {node_id}: {e}")
            return None
    
    def search_code_nodes(self, search_term: str, node_types: List[str] = None) -> List[Dict[str, Any]]:
        """Search for code nodes containing a term"""
        try:
            type_filter = ""
            if node_types:
                type_filter = f"AND n.type IN {node_types}"
            
            query = f"""
            MATCH (n:CodeNode)
            WHERE (n.name CONTAINS "{search_term}" OR n.content CONTAINS "{search_term}")
            {type_filter}
            RETURN n
            ORDER BY n.file_path, n.start_line
            LIMIT 50
            """
            
            result = self.neo4j.execute_query(query)
            return [dict(record['n']) for record in result] if result else []
            
        except Exception as e:
            logger.error(f"Error searching code nodes: {e}")
            return []
    
    def get_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Get the structure of a specific file"""
        try:
            escaped_path = self._escape_for_cypher(file_path)
            query = f"""
            MATCH (m:Module {{file_path: "{escaped_path}"}})
            OPTIONAL MATCH (m)-[:HAS_CLASS]->(c:Class)
            OPTIONAL MATCH (m)-[:HAS_FUNCTION]->(f:Function)
            OPTIONAL MATCH (m)-[:IMPORTS]->(i:Import)
            RETURN m,
                   collect(DISTINCT c) as classes,
                   collect(DISTINCT f) as functions,
                   collect(DISTINCT i) as imports
            """
            
            result = self.neo4j.execute_query(query)
            if result and len(result) > 0:
                record = result[0]
                return {
                    'module': dict(record['m']),
                    'classes': [dict(c) for c in record['classes'] if c],
                    'functions': [dict(f) for f in record['functions'] if f],
                    'imports': [dict(i) for i in record['imports'] if i]
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting file structure for {file_path}: {e}")
            return {}
    
    def clear_all_code_data(self) -> bool:
        """Clear all code-related data from Neo4j"""
        try:
            query = """
            MATCH (n:CodeNode)
            DETACH DELETE n
            """
            self.neo4j.execute_query(query)
            logger.info("Cleared all code data from Neo4j")
            return True
        except Exception as e:
            logger.error(f"Error clearing code data: {e}")
            return False
    
    def _escape_for_cypher(self, text: str) -> str:
        """Escape string for safe use in Cypher queries"""
        if not isinstance(text, str):
            return str(text)
        
        # Replace problematic characters
        escaped = text.replace('\\', '\\\\')  # Escape backslashes first
        escaped = escaped.replace('"', '\\"')   # Escape quotes
        escaped = escaped.replace("'", "\\'"')   # Escape single quotes
        escaped = escaped.replace('\n', '\\n')  # Escape newlines
        escaped = escaped.replace('\r', '\\r')  # Escape carriage returns
        escaped = escaped.replace('\t', '\\t')  # Escape tabs
        
        return escaped
    
    def _prepare_property_value(self, value) -> str:
        """Prepare property value for Cypher query with proper escaping"""
        if isinstance(value, str):
            return f'"{self._escape_for_cypher(value)}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # JSON encode and then escape for Cypher
            json_str = json.dumps(value, ensure_ascii=False)
            return f'"{self._escape_for_cypher(json_str)}"'
        elif value is None:
            return 'null'
        else:
            return f'"{self._escape_for_cypher(str(value))}"'
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the code graph"""
        try:
            stats_queries = {
                'total_nodes': "MATCH (n:CodeNode) RETURN count(n) as count",
                'total_relationships': "MATCH ()-[r]->() RETURN count(r) as count",
                'modules': "MATCH (n:Module) RETURN count(n) as count",
                'classes': "MATCH (n:Class) RETURN count(n) as count", 
                'functions': "MATCH (n:Function) RETURN count(n) as count",
                'imports': "MATCH (n:Import) RETURN count(n) as count"
            }
            
            stats = {}
            for stat_name, query in stats_queries.items():
                result = self.neo4j.execute_query(query)
                stats[stat_name] = result[0]['count'] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {}

# Global converter instance
ast_converter = ASTConverter()
