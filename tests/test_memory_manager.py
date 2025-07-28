import pytest
from unittest.mock import patch

from src.memory.memory_manager import MemoryManager

@patch('src.memory.neo4j_integration.Neo4jKnowledgeGraph')
@patch('src.memory.qdrant_integration.QdrantVectorStore')
def test_memory_manager_integration(mock_qdrant, mock_neo4j):
    """Test the integration of MemoryManager with Neo4j and Qdrant"""
    # Mock instances of Neo4j and Qdrant
    mock_neo4j_instance = mock_neo4j.return_value
    mock_qdrant_instance = mock_qdrant.return_value

    # Mock behaviors
    mock_neo4j_instance.connected = True
    mock_qdrant_instance.available = True

    # Initialize Memory Manager
    manager = MemoryManager()

    # Test Neo4j and Qdrant connections
    assert manager.knowledge_graph.connected is True, "Neo4j should be connected"
    assert mock_neo4j_instance.connected is True, "Mock Neo4j should be connected"
    assert mock_qdrant_instance.available is True, "Mock Qdrant should be available"

    # Test adding data
    node_id = manager.add_knowledge_node("test_node", {"name": "Test"}, "test")
    assert node_id is True, "Node should be added to Neo4j"
    
    memory_id = manager.add_context_memory("This is a test memory.", "test")
    assert memory_id is not None, "Memory should be added to Qdrant"

    # Check if methods were called
    mock_neo4j_instance.add_node.assert_called_with("test_node", {"name": "Test"}, "test")
    mock_qdrant_instance.add_memory.assert_called_once()  # Ensure Qdrant was used

pytest.main([__file__])

