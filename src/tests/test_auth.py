"""
Tests for authentication module
"""

import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient
from api.auth import (
    create_access_token,
    decode_jwt_token,
    generate_api_key,
    validate_permissions,
    API_KEYS,
    rate_limiter
)


class TestAuthentication:
    """Test authentication functionality"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test_user", "scopes": ["read", "write"]}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = decode_jwt_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert "exp" in payload
    
    def test_decode_expired_token(self):
        """Test handling of expired tokens"""
        data = {"sub": "test_user"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = decode_jwt_token(token)
        assert payload is None
    
    def test_decode_invalid_token(self):
        """Test handling of invalid tokens"""
        invalid_token = "invalid.token.here"
        payload = decode_jwt_token(invalid_token)
        assert payload is None
    
    def test_generate_api_key(self):
        """Test API key generation"""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        assert key1 != key2
        assert key1.startswith("kairos_")
        assert len(key1) > 30
    
    def test_validate_permissions(self):
        """Test permission validation"""
        # Test with known test key
        test_key = "test-key-123"
        
        assert validate_permissions(test_key, ["read"])
        assert validate_permissions(test_key, ["read", "write"])
        assert not validate_permissions(test_key, ["admin"])
        assert not validate_permissions("invalid-key", ["read"])
    
    def test_rate_limiter(self):
        """Test rate limiting functionality"""
        test_key = "test_rate_limit"
        
        # Should allow initial requests
        for i in range(10):
            assert rate_limiter.is_allowed(test_key)
        
        # Reset the limiter for clean test
        rate_limiter.requests = {}
        
        # Test rate limit
        for i in range(rate_limiter.requests_per_minute):
            assert rate_limiter.is_allowed(test_key)
        
        # Next request should be denied
        assert not rate_limiter.is_allowed(test_key)


class TestAPIKeySecurity:
    """Test API key security features"""
    
    def test_api_key_structure(self):
        """Test API key storage structure"""
        for key, data in API_KEYS.items():
            assert "name" in data
            assert "permissions" in data
            assert "created_at" in data
            assert isinstance(data["permissions"], list)
    
    def test_default_api_keys(self):
        """Test default API keys exist"""
        assert "test-key-123" in API_KEYS
        assert len(API_KEYS) >= 2  # At least test key and default key


@pytest.mark.asyncio
class TestWebSocketAuth:
    """Test WebSocket authentication"""
    
    async def test_websocket_auth_with_api_key(self):
        """Test WebSocket authentication with API key"""
        from api.auth import verify_websocket_auth
        
        # Mock WebSocket with API key
        class MockWebSocket:
            def __init__(self, api_key=None, token=None):
                self.query_params = {}
                if api_key:
                    self.query_params["apiKey"] = api_key
                if token:
                    self.query_params["token"] = token
                self.headers = {}
        
        # Test with valid API key
        ws = MockWebSocket(api_key="test-key-123")
        assert await verify_websocket_auth(ws)
        
        # Test with invalid API key
        ws = MockWebSocket(api_key="invalid-key")
        assert not await verify_websocket_auth(ws)
        
        # Test with no authentication
        ws = MockWebSocket()
        assert not await verify_websocket_auth(ws)
    
    async def test_websocket_auth_with_token(self):
        """Test WebSocket authentication with JWT token"""
        from api.auth import verify_websocket_auth
        
        # Create valid token
        token = create_access_token({"sub": "test_user"})
        
        class MockWebSocket:
            def __init__(self, token=None):
                self.query_params = {}
                if token:
                    self.query_params["token"] = token
                self.headers = {}
        
        # Test with valid token
        ws = MockWebSocket(token=token)
        assert await verify_websocket_auth(ws)
        
        # Test with invalid token
        ws = MockWebSocket(token="invalid.token")
        assert not await verify_websocket_auth(ws)
