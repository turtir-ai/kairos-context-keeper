"""
Tests for WebSocket Manager functionality
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock
from api.websocket_manager import WebSocketManager


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.is_closed = False
        self.accept = AsyncMock()
        self.send_text = AsyncMock(side_effect=self._record_message)
        self.send_json = AsyncMock(side_effect=self._record_json)
        self.close = AsyncMock(side_effect=self._close)
    
    async def _record_message(self, message):
        """Record sent messages"""
        if not self.is_closed:
            self.sent_messages.append(message)
    
    async def _record_json(self, data):
        """Record sent JSON messages"""
        if not self.is_closed:
            self.sent_messages.append(json.dumps(data))
    
    async def _close(self):
        """Mark as closed"""
        self.is_closed = True


class TestWebSocketManager:
    """Test WebSocket Manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocket manager instance"""
        return WebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        return MockWebSocket()
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, manager, mock_websocket):
        """Test WebSocket connection"""
        await manager.connect(mock_websocket)
        
        assert mock_websocket in manager.active_connections
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_websocket(self, manager, mock_websocket):
        """Test WebSocket disconnection"""
        # First connect
        manager.active_connections.add(mock_websocket)
        
        # Then disconnect
        manager.disconnect(mock_websocket)
        
        assert mock_websocket not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending message to specific WebSocket"""
        manager.active_connections.add(mock_websocket)
        
        await manager.send_personal_message("Test message", mock_websocket)
        
        mock_websocket.send_text.assert_called_once_with("Test message")
    
    @pytest.mark.asyncio
    async def test_send_personal_json(self, manager, mock_websocket):
        """Test sending JSON to specific WebSocket"""
        manager.active_connections.add(mock_websocket)
        
        test_data = {"type": "test", "value": 123}
        await manager.send_personal_json(test_data, mock_websocket)
        
        mock_websocket.send_json.assert_called_once_with(test_data)
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, manager):
        """Test broadcasting message to all connections"""
        # Create multiple mock connections
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        manager.active_connections = {ws1, ws2, ws3}
        
        test_data = {"type": "broadcast", "message": "Hello all"}
        await manager.broadcast(test_data)
        
        # All should receive the message
        for ws in [ws1, ws2, ws3]:
            ws.send_json.assert_called_once_with(test_data)
    
    @pytest.mark.asyncio
    async def test_broadcast_with_failed_connection(self, manager):
        """Test broadcasting handles failed connections gracefully"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        # Make ws2 fail
        ws2.send_json.side_effect = Exception("Connection closed")
        
        manager.active_connections = {ws1, ws2, ws3}
        
        test_data = {"type": "broadcast", "message": "Test"}
        await manager.broadcast(test_data)
        
        # ws2 should be removed from active connections
        assert ws2 not in manager.active_connections
        assert ws1 in manager.active_connections
        assert ws3 in manager.active_connections
    
    def test_subscribe_to_topic(self, manager, mock_websocket):
        """Test subscribing to a topic"""
        topic = "agent_updates"
        manager.subscribe(mock_websocket, topic)
        
        assert topic in manager.subscriptions
        assert mock_websocket in manager.subscriptions[topic]
    
    def test_unsubscribe_from_topic(self, manager, mock_websocket):
        """Test unsubscribing from a topic"""
        topic = "agent_updates"
        
        # First subscribe
        manager.subscribe(mock_websocket, topic)
        assert mock_websocket in manager.subscriptions[topic]
        
        # Then unsubscribe
        manager.unsubscribe(mock_websocket, topic)
        assert mock_websocket not in manager.subscriptions[topic]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self, manager):
        """Test broadcasting to topic subscribers only"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        # Subscribe ws1 and ws2 to topic
        manager.subscribe(ws1, "updates")
        manager.subscribe(ws2, "updates")
        
        # ws3 is not subscribed
        manager.active_connections = {ws1, ws2, ws3}
        
        test_data = {"type": "update", "data": "test"}
        await manager.broadcast_to_topic("updates", test_data)
        
        # Only ws1 and ws2 should receive the message
        ws1.send_json.assert_called_once_with(test_data)
        ws2.send_json.assert_called_once_with(test_data)
        ws3.send_json.assert_not_called()
    
    def test_disconnect_removes_subscriptions(self, manager):
        """Test that disconnect removes all subscriptions"""
        ws = MockWebSocket()
        
        # Subscribe to multiple topics
        manager.subscribe(ws, "topic1")
        manager.subscribe(ws, "topic2")
        manager.subscribe(ws, "topic3")
        
        # Add to active connections
        manager.active_connections.add(ws)
        
        # Disconnect
        manager.disconnect(ws)
        
        # Should be removed from all subscriptions
        for topic in ["topic1", "topic2", "topic3"]:
            assert ws not in manager.subscriptions.get(topic, set())
    
    @pytest.mark.asyncio
    async def test_send_to_connection_id(self, manager):
        """Test sending message by connection ID"""
        ws = MockWebSocket()
        conn_id = "test-connection-123"
        
        # Map connection ID
        manager.active_connections.add(ws)
        manager.connection_ids[ws] = conn_id
        
        test_data = {"type": "personal", "data": "test"}
        success = await manager.send_to_connection(conn_id, test_data)
        
        assert success
        ws.send_json.assert_called_once_with(test_data)
    
    @pytest.mark.asyncio
    async def test_send_to_invalid_connection_id(self, manager):
        """Test sending to invalid connection ID"""
        test_data = {"type": "test"}
        success = await manager.send_to_connection("invalid-id", test_data)
        
        assert not success
    
    def test_get_connection_count(self, manager):
        """Test getting active connection count"""
        assert manager.get_connection_count() == 0
        
        # Add connections
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        manager.active_connections = {ws1, ws2}
        
        assert manager.get_connection_count() == 2
    
    def test_get_subscriptions_for_topic(self, manager):
        """Test getting subscribers for a topic"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        manager.subscribe(ws1, "updates")
        manager.subscribe(ws2, "updates")
        manager.subscribe(ws1, "alerts")
        
        updates_subs = manager.get_subscribers("updates")
        assert len(updates_subs) == 2
        assert ws1 in updates_subs
        assert ws2 in updates_subs
        
        alerts_subs = manager.get_subscribers("alerts")
        assert len(alerts_subs) == 1
        assert ws1 in alerts_subs
