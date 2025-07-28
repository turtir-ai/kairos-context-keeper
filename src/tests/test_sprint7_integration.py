"""
Comprehensive integration tests for Sprint 7 features
Tests RBAC, audit logging, rate limiting, and admin functionality
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as redis
import asyncpg

from src.main import app
from src.api.rbac_middleware import RBACManager, Permission, RolePermissionMatrix
from src.api.rate_limiting import RateLimiter, RateLimit, RateLimitType
from src.database.models.audit import AuditLogger, AuditEventType, AuditSeverity
from src.database.models.user import User, UserRole, UserStatus


class TestSprint7Integration:
    """Integration tests for Sprint 7 features"""
    
    @pytest.fixture
    async def mock_db_pool(self):
        """Mock database pool"""
        pool = AsyncMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool
    
    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis client"""
        redis_client = AsyncMock()
        return redis_client
    
    @pytest.fixture
    async def rbac_manager(self, mock_db_pool):
        """Create RBAC manager with mocked dependencies"""
        return RBACManager(mock_db_pool)
    
    @pytest.fixture
    async def rate_limiter(self, mock_redis):
        """Create rate limiter with mocked dependencies"""
        return RateLimiter(mock_redis)
    
    @pytest.fixture
    async def audit_logger(self, mock_db_pool):
        """Create audit logger with mocked dependencies"""
        logger = AuditLogger(mock_db_pool)
        return logger
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)


class TestRBACSystem:
    """Test Role-Based Access Control system"""
    
    @pytest.mark.asyncio
    async def test_permission_matrix(self):
        """Test role permission matrix"""
        # Test super admin permissions
        super_admin_perms = RolePermissionMatrix.get_permissions(UserRole.SUPER_ADMIN.value)
        assert Permission.SYSTEM_ADMIN in super_admin_perms
        assert Permission.PROJECT_DELETE in super_admin_perms
        assert len(super_admin_perms) > 20  # Should have many permissions
        
        # Test viewer permissions
        viewer_perms = RolePermissionMatrix.get_permissions(UserRole.VIEWER.value)
        assert Permission.PROJECT_READ in viewer_perms
        assert Permission.SYSTEM_ADMIN not in viewer_perms
        assert Permission.PROJECT_DELETE not in viewer_perms
        assert len(viewer_perms) < 10  # Should have limited permissions
    
    @pytest.mark.asyncio
    async def test_user_permission_check(self, rbac_manager, mock_db_pool):
        """Test user permission checking"""
        # Mock user data
        mock_user = {
            'id': 'user123',
            'role': 'admin',
            'status': 'active'
        }
        
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = mock_user
        
        # Test admin permission
        has_permission = await rbac_manager.check_permission(
            user_id='user123',
            permission=Permission.PROJECT_CREATE
        )
        assert has_permission is True
        
        # Test permission user doesn't have
        has_permission = await rbac_manager.check_permission(
            user_id='user123', 
            permission=Permission.SYSTEM_ADMIN
        )
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_inactive_user_permissions(self, rbac_manager, mock_db_pool):
        """Test that inactive users have no permissions"""
        mock_user = {
            'id': 'user123',
            'role': 'admin',
            'status': 'inactive'
        }
        
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = mock_user
        
        has_permission = await rbac_manager.check_permission(
            user_id='user123',
            permission=Permission.PROJECT_READ
        )
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_project_specific_permissions(self, rbac_manager, mock_db_pool):
        """Test project-specific permission checking"""
        mock_user = {
            'id': 'user123',
            'role': 'user',
            'status': 'active'
        }
        
        # Mock database calls
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = mock_user
        conn.fetchval.return_value = 'member'  # Project role
        
        has_permission = await rbac_manager.check_permission(
            user_id='user123',
            permission=Permission.TASK_CREATE,
            project_id='proj123'
        )
        assert has_permission is True


class TestAuditLogging:
    """Test audit logging system"""
    
    @pytest.mark.asyncio
    async def test_basic_audit_log(self, audit_logger, mock_db_pool):
        """Test basic audit event logging"""
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {'username': 'testuser', 'email': 'test@example.com'}
        
        await audit_logger.log_event(
            event_type=AuditEventType.USER_CREATED,
            user_id='user123',
            severity=AuditSeverity.MEDIUM,
            details={'new_user': 'test@example.com'},
            ip_address='192.168.1.1'
        )
        
        # Verify database insert was called
        conn.execute.assert_called()
        call_args = conn.execute.call_args[0]
        assert 'INSERT INTO audit_logs' in call_args[0]
        assert AuditEventType.USER_CREATED.value in call_args
    
    @pytest.mark.asyncio
    async def test_auth_event_logging(self, audit_logger, mock_db_pool):
        """Test authentication event logging"""
        await audit_logger.log_auth_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id='user123',
            email='test@example.com',
            ip_address='192.168.1.1',
            success=True
        )
        
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        assert conn.execute.call_count >= 2  # Should log to both tables
    
    @pytest.mark.asyncio
    async def test_security_event_logging(self, audit_logger, mock_db_pool):
        """Test security event logging"""
        await audit_logger.log_security_event(
            event_type=AuditEventType.BRUTE_FORCE_ATTEMPT,
            severity=AuditSeverity.CRITICAL,
            source_ip='192.168.1.100',
            details={'attempt_count': 10}
        )
        
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limit_detection(self, audit_logger, mock_db_pool):
        """Test rate limit violation detection"""
        # Mock rate limit check
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchval.return_value = 10  # Simulate 10 events in window
        
        # This should trigger rate limit detection
        with patch.object(audit_logger, 'log_security_event') as mock_security_log:
            await audit_logger._check_rate_limit(
                AuditEventType.LOGIN_FAILED,
                user_id='user123',
                ip_address='192.168.1.100'
            )
            
            mock_security_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_audit_log_retrieval(self, audit_logger, mock_db_pool):
        """Test audit log retrieval with filtering"""
        # Mock database response
        mock_logs = [
            {
                'id': 'log1',
                'event_type': 'user_created',
                'user_id': 'user123',
                'timestamp': datetime.now(),
                'success': True,
                'action_details': '{}',
                'severity': 'medium'
            }
        ]
        
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetch.return_value = mock_logs
        
        logs = await audit_logger.get_audit_logs(
            user_id='user123',
            event_type=AuditEventType.USER_CREATED,
            limit=50
        )
        
        assert len(logs) == 1
        assert logs[0]['event_type'] == 'user_created'


class TestRateLimiting:
    """Test rate limiting system"""
    
    @pytest.mark.asyncio
    async def test_sliding_window_rate_limit(self, rate_limiter, mock_redis):
        """Test sliding window rate limiting"""
        # Mock Redis responses
        mock_redis.pipeline.return_value.execute.return_value = [None, 5, None, None]  # 5 current requests
        
        from fastapi import Request
        
        # Create mock request
        request = MagicMock(spec=Request)
        request.url.path = '/api/test'
        request.client.host = '192.168.1.1'
        request.headers.get.return_value = None
        
        status = await rate_limiter.check_rate_limit(
            request=request,
            user_id='user123',
            user_role='user'
        )
        
        assert status.allowed is True
        assert status.requests_remaining >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit exceeded scenario"""
        # Mock Redis to return limit exceeded
        mock_redis.pipeline.return_value.execute.return_value = [None, 201, None, None]  # Over limit
        
        from fastapi import Request
        request = MagicMock(spec=Request)
        request.url.path = '/api/test'
        request.client.host = '192.168.1.1'
        request.headers.get.return_value = None
        
        status = await rate_limiter.check_rate_limit(
            request=request,
            user_id='user123',
            user_role='user'
        )
        
        assert status.allowed is False
        assert status.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self, rate_limiter):
        """Test endpoint-specific rate limits"""
        from src.api.rate_limiting import RateLimitConfig
        
        config = RateLimitConfig()
        
        # Auth endpoints should have stricter limits
        auth_limit = config.ENDPOINT_LIMITS['/api/auth/login']
        assert auth_limit.requests == 5  # Very strict
        
        # General API endpoints should have higher limits
        api_limit = config.USER_LIMITS['user']
        assert api_limit.requests == 200  # More generous
    
    @pytest.mark.asyncio
    async def test_ip_whitelist(self, rate_limiter):
        """Test IP whitelisting"""
        from fastapi import Request
        
        request = MagicMock(spec=Request)
        request.url.path = '/api/test'
        request.client.host = '127.0.0.1'  # Localhost should be whitelisted
        request.headers.get.return_value = None
        
        status = await rate_limiter.check_rate_limit(request=request)
        
        assert status.allowed is True
        assert status.requests_remaining == 999999  # Unlimited for whitelisted
    
    @pytest.mark.asyncio
    async def test_suspicious_ip_flagging(self, rate_limiter, mock_redis):
        """Test suspicious IP flagging"""
        ip = '192.168.1.100'
        
        # Simulate multiple violations
        await rate_limiter._log_rate_limit_violation(
            ip=ip,
            user_id=None,
            endpoint='/api/test',
            limit_type='ip',
            identifier=ip
        )
        
        # Mock Redis to simulate violation count
        mock_redis.incr.return_value = 15  # Over threshold
        
        # Should flag IP as suspicious
        mock_redis.sadd.assert_called_with('suspicious_ips', ip)


class TestAdminEndpoints:
    """Test admin API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_users_endpoint(self, test_client):
        """Test admin users endpoint"""
        with patch('src.api.admin_routes.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'admin123', 'role': 'admin'}
            
            with patch('src.api.admin_routes.get_rbac_manager') as mock_rbac:
                mock_manager = MagicMock()
                mock_manager.user_model.list_users.return_value = [
                    {
                        'id': 'user1',
                        'email': 'user1@example.com',
                        'username': 'user1',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'role': 'user',
                        'status': 'active',
                        'created_at': datetime.now(),
                        'last_login': datetime.now()
                    }
                ]
                mock_manager.user_model.get_user_projects.return_value = []
                mock_rbac.return_value = mock_manager
                
                response = test_client.get('/api/admin/users')
                
                assert response.status_code == 200
                data = response.json()
                assert 'users' in data
    
    @pytest.mark.asyncio
    async def test_invite_user_endpoint(self, test_client):
        """Test user invitation endpoint"""
        with patch('src.api.admin_routes.get_current_admin_user') as mock_auth:
            mock_auth.return_value = {'user_id': 'admin123', 'role': 'admin'}
            
            with patch('src.api.admin_routes.get_rbac_manager') as mock_rbac:
                mock_manager = MagicMock()
                mock_manager.user_model.get_user_by_email.return_value = None  # User doesn't exist
                mock_manager.db_pool.acquire.return_value.__aenter__.return_value.execute = AsyncMock()
                mock_manager.audit_logger.log_event = AsyncMock()
                mock_rbac.return_value = mock_manager
                
                invitation_data = {
                    'email': 'newuser@example.com',
                    'firstName': 'Jane',
                    'lastName': 'Smith',
                    'role': 'user',
                    'message': 'Welcome to Kairos!'
                }
                
                response = test_client.post('/api/admin/invite', json=invitation_data)
                
                assert response.status_code == 200
                data = response.json()
                assert 'invitation_id' in data
    
    @pytest.mark.asyncio
    async def test_unauthorized_admin_access(self, test_client):
        """Test unauthorized access to admin endpoints"""
        # No authentication provided
        response = test_client.get('/api/admin/users')
        assert response.status_code == 401
        
        # Non-admin user
        with patch('src.api.admin_routes.get_current_admin_user') as mock_auth:
            mock_auth.side_effect = HTTPException(status_code=403, detail="Admin permissions required")
            
            response = test_client.get('/api/admin/users')
            assert response.status_code == 403


class TestSystemIntegration:
    """Test system-wide integration"""
    
    @pytest.mark.asyncio
    async def test_full_user_workflow(self, mock_db_pool, mock_redis):
        """Test complete user management workflow"""
        # Initialize systems
        rbac_manager = RBACManager(mock_db_pool)
        audit_logger = AuditLogger(mock_db_pool)
        
        # Mock database responses
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        
        # Test user creation
        conn.fetchrow.return_value = None  # User doesn't exist
        conn.execute.return_value = None
        
        # Test authentication
        mock_user = {
            'id': 'user123',
            'email': 'test@example.com',
            'role': 'user',
            'status': 'active'
        }
        conn.fetchrow.return_value = mock_user
        
        # Test permission check
        has_permission = await rbac_manager.check_permission(
            user_id='user123',
            permission=Permission.PROJECT_READ
        )
        assert has_permission is True
        
        # Test audit logging
        await audit_logger.log_event(
            event_type=AuditEventType.USER_CREATED,
            user_id='user123',
            severity=AuditSeverity.MEDIUM
        )
        
        # Verify all systems worked together
        assert conn.execute.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_security_incident_response(self, mock_db_pool, mock_redis):
        """Test security incident detection and response"""
        audit_logger = AuditLogger(mock_db_pool)
        rate_limiter = RateLimiter(mock_redis)
        
        # Simulate multiple failed login attempts
        for i in range(10):
            await audit_logger.log_auth_event(
                event_type=AuditEventType.LOGIN_FAILED,
                email='attacker@evil.com',
                ip_address='192.168.1.100',
                success=False,
                failure_reason='Invalid credentials'
            )
        
        # Should trigger security monitoring
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        assert conn.execute.call_count >= 10
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, mock_db_pool, mock_redis):
        """Test system performance under load"""
        rbac_manager = RBACManager(mock_db_pool)
        
        # Mock fast database responses
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {
            'id': 'user123',
            'role': 'user',
            'status': 'active'
        }
        
        # Simulate many concurrent permission checks
        tasks = []
        for i in range(100):
            task = rbac_manager.check_permission(
                user_id=f'user{i}',
                permission=Permission.PROJECT_READ
            )
            tasks.append(task)
        
        # All should complete successfully
        results = await asyncio.gather(*tasks)
        assert all(results)  # All permission checks should pass


class TestErrorHandling:
    """Test error handling and resilience"""
    
    @pytest.mark.asyncio
    async def test_database_failure_handling(self, mock_db_pool):
        """Test handling of database failures"""
        # Mock database failure
        mock_db_pool.acquire.side_effect = Exception("Database connection failed")
        
        rbac_manager = RBACManager(mock_db_pool)
        
        # Should handle gracefully
        result = await rbac_manager.check_permission(
            user_id='user123',
            permission=Permission.PROJECT_READ
        )
        assert result is False  # Fail safe
    
    @pytest.mark.asyncio
    async def test_redis_failure_handling(self, mock_redis):
        """Test handling of Redis failures"""
        # Mock Redis failure
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")
        
        rate_limiter = RateLimiter(mock_redis)
        
        from fastapi import Request
        request = MagicMock(spec=Request)
        request.url.path = '/api/test'
        request.client.host = '192.168.1.1'
        request.headers.get.return_value = None
        
        # Should fail open (allow request)
        status = await rate_limiter.check_rate_limit(request=request)
        assert status.allowed is True  # Fail open for availability
    
    @pytest.mark.asyncio
    async def test_audit_logging_resilience(self, mock_db_pool):
        """Test audit logging resilience to failures"""
        # Mock database failure
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.execute.side_effect = Exception("Database write failed")
        
        audit_logger = AuditLogger(mock_db_pool)
        
        # Should not raise exception
        try:
            await audit_logger.log_event(
                event_type=AuditEventType.USER_CREATED,
                user_id='user123'
            )
        except Exception:
            pytest.fail("Audit logging should handle database failures gracefully")


# Performance benchmarks
class TestPerformance:
    """Performance tests for Sprint 7 features"""
    
    @pytest.mark.asyncio
    async def test_rbac_performance(self, mock_db_pool):
        """Test RBAC system performance"""
        rbac_manager = RBACManager(mock_db_pool)
        
        # Mock fast database response
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.fetchrow.return_value = {
            'id': 'user123',
            'role': 'user', 
            'status': 'active'
        }
        
        start_time = time.time()
        
        # Perform 1000 permission checks
        for _ in range(1000):
            await rbac_manager.check_permission(
                user_id='user123',
                permission=Permission.PROJECT_READ
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (< 1 second for 1000 checks)
        assert duration < 1.0, f"RBAC performance too slow: {duration:.2f}s for 1000 checks"
    
    @pytest.mark.asyncio 
    async def test_audit_logging_performance(self, mock_db_pool):
        """Test audit logging performance"""
        audit_logger = AuditLogger(mock_db_pool)
        
        start_time = time.time()
        
        # Log 1000 events
        tasks = []
        for i in range(1000):
            task = audit_logger.log_event(
                event_type=AuditEventType.USER_CREATED,
                user_id=f'user{i}',
                details={'test': i}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 2.0, f"Audit logging too slow: {duration:.2f}s for 1000 events"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
