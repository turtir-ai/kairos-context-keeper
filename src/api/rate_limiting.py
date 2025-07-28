"""
Advanced API Rate Limiting System for Kairos
Provides multiple rate limiting strategies for different user types and endpoints.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from enum import Enum
import redis.asyncio as redis
import logging
from dataclasses import dataclass, asdict


class RateLimitType(Enum):
    """Types of rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window" 
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int  # Number of requests
    window: int    # Time window in seconds
    limit_type: RateLimitType = RateLimitType.SLIDING_WINDOW
    burst_multiplier: float = 1.5  # Allow burst up to this multiplier


@dataclass
class RateLimitStatus:
    """Current rate limit status"""
    allowed: bool
    requests_remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class RateLimitConfig:
    """Rate limit configurations for different user types and endpoints"""
    
    # User-based rate limits (per minute)
    USER_LIMITS = {
        "super_admin": RateLimit(requests=1000, window=60),
        "admin": RateLimit(requests=500, window=60),
        "user": RateLimit(requests=200, window=60),
        "viewer": RateLimit(requests=100, window=60),
        "anonymous": RateLimit(requests=20, window=60)
    }
    
    # Endpoint-specific rate limits (per minute)
    ENDPOINT_LIMITS = {
        # Authentication endpoints (stricter limits)
        "/api/auth/login": RateLimit(requests=5, window=60),
        "/api/auth/register": RateLimit(requests=3, window=300),  # 5 minutes
        "/api/auth/reset-password": RateLimit(requests=2, window=300),
        
        # AI/LLM endpoints (resource intensive)
        "/api/ai/generate": RateLimit(requests=50, window=60),
        "/api/ai/analyze": RateLimit(requests=30, window=60),
        "/api/mcp/execute": RateLimit(requests=100, window=60),
        
        # Admin endpoints
        "/api/admin/users": RateLimit(requests=50, window=60),
        "/api/admin/invite": RateLimit(requests=10, window=60),
        "/api/admin/audit-logs": RateLimit(requests=100, window=60),
        
        # Data endpoints
        "/api/memory/query": RateLimit(requests=200, window=60),
        "/api/memory/store": RateLimit(requests=100, window=60),
        
        # Task/workflow endpoints
        "/api/orchestration/tasks": RateLimit(requests=150, window=60),
        "/api/orchestration/workflows": RateLimit(requests=100, window=60),
        
        # File upload endpoints
        "/api/upload": RateLimit(requests=20, window=60),
        "/api/export": RateLimit(requests=10, window=300),  # 5 minutes
    }
    
    # IP-based rate limits (global protection)
    IP_LIMITS = {
        "default": RateLimit(requests=300, window=60),
        "suspicious": RateLimit(requests=10, window=300),  # Flagged IPs
    }
    
    # Project-based rate limits
    PROJECT_LIMITS = {
        "free": RateLimit(requests=500, window=3600),    # per hour
        "paid": RateLimit(requests=2000, window=3600),   # per hour
        "enterprise": RateLimit(requests=10000, window=3600)  # per hour
    }


class RateLimiter:
    """Advanced rate limiting implementation with multiple strategies"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.config = RateLimitConfig()
        
        # Cache for frequently accessed limits
        self.limit_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Whitelist for certain IPs/users
        self.whitelisted_ips = set()
        self.whitelisted_users = set()
        
        self.logger.info("🚦 Advanced Rate Limiter initialized")
    
    async def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        project_id: Optional[str] = None,
        endpoint_override: Optional[str] = None
    ) -> RateLimitStatus:
        """
        Check rate limits using multiple strategies
        Returns RateLimitStatus indicating if request should be allowed
        """
        try:
            client_ip = self._get_client_ip(request)
            endpoint = endpoint_override or self._normalize_endpoint(request.url.path)
            
            # Check whitelist first
            if self._is_whitelisted(client_ip, user_id):
                return RateLimitStatus(
                    allowed=True,
                    requests_remaining=999999,
                    reset_time=int(time.time()) + 3600
                )
            
            # Collect all applicable rate limits
            limits_to_check = []
            
            # 1. IP-based limit (global protection)
            ip_limit = await self._get_ip_limit(client_ip)
            limits_to_check.append(("ip", client_ip, ip_limit))
            
            # 2. User-based limit
            if user_id and user_role:
                user_limit = self.config.USER_LIMITS.get(
                    user_role, 
                    self.config.USER_LIMITS["user"]
                )
                limits_to_check.append(("user", user_id, user_limit))
            
            # 3. Endpoint-specific limit
            if endpoint in self.config.ENDPOINT_LIMITS:
                endpoint_limit = self.config.ENDPOINT_LIMITS[endpoint]
                limits_to_check.append(("endpoint", f"{endpoint}:{client_ip}", endpoint_limit))
            
            # 4. Project-based limit (if applicable)
            if project_id:
                project_limit = await self._get_project_limit(project_id)
                limits_to_check.append(("project", project_id, project_limit))
            
            # Check each limit
            most_restrictive = None
            for limit_type, identifier, limit_config in limits_to_check:
                status = await self._check_individual_limit(
                    limit_type, identifier, limit_config
                )
                
                if not status.allowed:
                    # Log rate limit violation
                    await self._log_rate_limit_violation(
                        client_ip, user_id, endpoint, limit_type, identifier
                    )
                    return status
                
                # Track the most restrictive allowed limit
                if most_restrictive is None or status.requests_remaining < most_restrictive.requests_remaining:
                    most_restrictive = status
            
            return most_restrictive or RateLimitStatus(
                allowed=True,
                requests_remaining=100,
                reset_time=int(time.time()) + 60
            )
            
        except Exception as e:
            self.logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return RateLimitStatus(
                allowed=True,
                requests_remaining=0,
                reset_time=int(time.time()) + 60
            )
    
    async def _check_individual_limit(
        self,
        limit_type: str,
        identifier: str,
        limit_config: RateLimit
    ) -> RateLimitStatus:
        """Check an individual rate limit"""
        key = f"rate_limit:{limit_type}:{identifier}"
        
        if limit_config.limit_type == RateLimitType.SLIDING_WINDOW:
            return await self._sliding_window_check(key, limit_config)
        elif limit_config.limit_type == RateLimitType.TOKEN_BUCKET:
            return await self._token_bucket_check(key, limit_config)
        else:
            # Default to fixed window
            return await self._fixed_window_check(key, limit_config)
    
    async def _sliding_window_check(
        self,
        key: str,
        limit_config: RateLimit
    ) -> RateLimitStatus:
        """Sliding window rate limiting implementation"""
        now = time.time()
        window_start = now - limit_config.window
        
        # Use Redis sorted set for sliding window
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, limit_config.window + 10)
        
        results = await pipe.execute()
        current_count = results[1]
        
        allowed = current_count < limit_config.requests
        remaining = max(0, limit_config.requests - current_count - 1)  # -1 for current request
        reset_time = int(now) + limit_config.window
        
        if not allowed:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(key, str(now))
            remaining = 0
            # Calculate retry_after based on oldest request in window
            oldest_request = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                retry_after = int(oldest_request[0][1] + limit_config.window - now) + 1
            else:
                retry_after = limit_config.window
        else:
            retry_after = None
        
        return RateLimitStatus(
            allowed=allowed,
            requests_remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after
        )
    
    async def _fixed_window_check(
        self,
        key: str,
        limit_config: RateLimit
    ) -> RateLimitStatus:
        """Fixed window rate limiting implementation"""
        now = int(time.time())
        window_start = (now // limit_config.window) * limit_config.window
        window_key = f"{key}:{window_start}"
        
        # Increment counter
        current_count = await self.redis.incr(window_key)
        
        if current_count == 1:
            # Set expiry for new window
            await self.redis.expire(window_key, limit_config.window)
        
        allowed = current_count <= limit_config.requests
        remaining = max(0, limit_config.requests - current_count)
        reset_time = window_start + limit_config.window
        
        retry_after = None
        if not allowed:
            retry_after = reset_time - now
        
        return RateLimitStatus(
            allowed=allowed,
            requests_remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after
        )
    
    async def _token_bucket_check(
        self,
        key: str,
        limit_config: RateLimit
    ) -> RateLimitStatus:
        """Token bucket rate limiting implementation"""
        now = time.time()
        bucket_key = f"{key}:bucket"
        
        # Get current bucket state
        bucket_data = await self.redis.hmget(
            bucket_key, 
            ["tokens", "last_refill"]
        )
        
        tokens = float(bucket_data[0]) if bucket_data[0] else limit_config.requests
        last_refill = float(bucket_data[1]) if bucket_data[1] else now
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = (time_elapsed / limit_config.window) * limit_config.requests
        tokens = min(limit_config.requests, tokens + tokens_to_add)
        
        allowed = tokens >= 1.0
        
        if allowed:
            tokens -= 1.0
        
        # Update bucket state
        await self.redis.hmset(bucket_key, {
            "tokens": str(tokens),
            "last_refill": str(now)
        })
        await self.redis.expire(bucket_key, limit_config.window * 2)
        
        return RateLimitStatus(
            allowed=allowed,
            requests_remaining=int(tokens),
            reset_time=int(now + limit_config.window),
            retry_after=1 if not allowed else None
        )
    
    async def _get_ip_limit(self, ip: str) -> RateLimit:
        """Get rate limit for IP address"""
        # Check if IP is flagged as suspicious
        is_suspicious = await self.redis.sismember("suspicious_ips", ip)
        
        if is_suspicious:
            return self.config.IP_LIMITS["suspicious"]
        else:
            return self.config.IP_LIMITS["default"]
    
    async def _get_project_limit(self, project_id: str) -> RateLimit:
        """Get rate limit for project based on subscription tier"""
        # This would typically query database for project subscription
        # For now, return default
        return self.config.PROJECT_LIMITS["free"]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded IP headers (common in load balancer setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for rate limiting"""
        # Remove query parameters
        path = path.split("?")[0]
        
        # Replace dynamic path segments with placeholders
        path_parts = path.split("/")
        normalized_parts = []
        
        for part in path_parts:
            # Replace UUIDs and numeric IDs with placeholders
            if self._is_uuid(part) or part.isdigit():
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)
        
        return "/".join(normalized_parts)
    
    def _is_uuid(self, value: str) -> bool:
        """Check if string is a UUID"""
        try:
            import uuid
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _is_whitelisted(self, ip: str, user_id: Optional[str]) -> bool:
        """Check if IP or user is whitelisted"""
        if ip in self.whitelisted_ips:
            return True
        
        if user_id and user_id in self.whitelisted_users:
            return True
        
        # Check for localhost/development
        if ip in ["127.0.0.1", "::1", "localhost"]:
            return True
        
        return False
    
    async def _log_rate_limit_violation(
        self,
        ip: str,
        user_id: Optional[str],
        endpoint: str,
        limit_type: str,
        identifier: str
    ):
        """Log rate limit violations for monitoring"""
        violation_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "ip": ip,
            "user_id": user_id,
            "endpoint": endpoint,
            "limit_type": limit_type,
            "identifier": identifier
        }
        
        # Log to Redis for real-time monitoring
        await self.redis.lpush(
            "rate_limit_violations",
            json.dumps(violation_data)
        )
        
        # Keep only recent violations
        await self.redis.ltrim("rate_limit_violations", 0, 999)
        
        # Check for repeated violations (potential attack)
        violations_key = f"violations:{ip}"
        violation_count = await self.redis.incr(violations_key)
        await self.redis.expire(violations_key, 300)  # 5 minutes
        
        if violation_count >= 10:  # Too many violations
            await self._flag_suspicious_ip(ip)
        
        self.logger.warning(
            f"Rate limit violation: {limit_type} limit exceeded for {identifier} "
            f"from IP {ip} on endpoint {endpoint}"
        )
    
    async def _flag_suspicious_ip(self, ip: str):
        """Flag IP as suspicious for enhanced rate limiting"""
        await self.redis.sadd("suspicious_ips", ip)
        await self.redis.expire("suspicious_ips", 3600)  # 1 hour
        
        self.logger.warning(f"IP {ip} flagged as suspicious due to repeated violations")
    
    async def add_to_whitelist(self, ip: str = None, user_id: str = None):
        """Add IP or user to whitelist"""
        if ip:
            self.whitelisted_ips.add(ip)
            await self.redis.sadd("whitelisted_ips", ip)
        
        if user_id:
            self.whitelisted_users.add(user_id)
            await self.redis.sadd("whitelisted_users", user_id)
    
    async def remove_from_whitelist(self, ip: str = None, user_id: str = None):
        """Remove IP or user from whitelist"""
        if ip:
            self.whitelisted_ips.discard(ip)
            await self.redis.srem("whitelisted_ips", ip)
        
        if user_id:
            self.whitelisted_users.discard(user_id)
            await self.redis.srem("whitelisted_users", user_id)
    
    async def get_rate_limit_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            # Get violations from last N hours
            violations = await self.redis.lrange("rate_limit_violations", 0, -1)
            
            stats = {
                "total_violations": len(violations),
                "violations_by_endpoint": {},
                "violations_by_ip": {},
                "violations_by_type": {},
                "suspicious_ips": list(await self.redis.smembers("suspicious_ips")),
                "whitelisted_ips": list(self.whitelisted_ips),
                "whitelisted_users": list(self.whitelisted_users)
            }
            
            # Analyze violations
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            for violation_json in violations:
                try:
                    violation = json.loads(violation_json)
                    violation_time = datetime.fromisoformat(violation["timestamp"])
                    
                    if violation_time >= cutoff_time:
                        # Count by endpoint
                        endpoint = violation["endpoint"]
                        stats["violations_by_endpoint"][endpoint] = stats["violations_by_endpoint"].get(endpoint, 0) + 1
                        
                        # Count by IP
                        ip = violation["ip"]
                        stats["violations_by_ip"][ip] = stats["violations_by_ip"].get(ip, 0) + 1
                        
                        # Count by type
                        limit_type = violation["limit_type"]
                        stats["violations_by_type"][limit_type] = stats["violations_by_type"].get(limit_type, 0) + 1
                        
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get rate limit stats: {e}")
            return {"error": str(e)}
    
    async def reset_user_limits(self, user_id: str):
        """Reset all rate limits for a specific user (admin function)"""
        patterns = [
            f"rate_limit:user:{user_id}",
            f"rate_limit:user:{user_id}:*"
        ]
        
        for pattern in patterns:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        
        self.logger.info(f"Reset rate limits for user {user_id}")
    
    async def cleanup_old_data(self):
        """Clean up old rate limiting data"""
        try:
            # Clean up old violations (keep last 1000)
            await self.redis.ltrim("rate_limit_violations", 0, 999)
            
            # Clean up expired rate limit keys
            # This is typically handled by Redis TTL, but we can do manual cleanup
            
            self.logger.info("Rate limiting data cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Rate limiting cleanup failed: {e}")


# Middleware function for FastAPI
async def rate_limit_middleware(
    request: Request,
    rate_limiter: RateLimiter,
    user_context: Optional[Dict[str, Any]] = None
):
    """Rate limiting middleware for FastAPI"""
    
    # Extract user information
    user_id = None
    user_role = "anonymous"
    project_id = None
    
    if user_context:
        user_id = user_context.get("user_id")
        user_role = user_context.get("role", "user")
        project_id = request.headers.get("X-Project-ID")
    
    # Check rate limits
    status = await rate_limiter.check_rate_limit(
        request=request,
        user_id=user_id,
        user_role=user_role,
        project_id=project_id
    )
    
    if not status.allowed:
        # Add rate limit headers for client
        headers = {
            "X-RateLimit-Limit": str(rate_limiter.config.USER_LIMITS.get(user_role, rate_limiter.config.USER_LIMITS["user"]).requests),
            "X-RateLimit-Remaining": str(status.requests_remaining),
            "X-RateLimit-Reset": str(status.reset_time),
        }
        
        if status.retry_after:
            headers["Retry-After"] = str(status.retry_after)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers=headers
        )
    
    # Add rate limit headers for successful requests
    request.state.rate_limit_remaining = status.requests_remaining
    request.state.rate_limit_reset = status.reset_time


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None

def init_rate_limiter(redis_client: redis.Redis):
    """Initialize global rate limiter"""
    global _rate_limiter
    _rate_limiter = RateLimiter(redis_client)

def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    if not _rate_limiter:
        raise RuntimeError("Rate limiter not initialized")
    return _rate_limiter


class RateLimiterMiddleware:
    """ASGI Middleware for rate limiting"""
    
    def __init__(self, app, redis_url: str = "redis://localhost:6379"):
        self.app = app
        import redis.asyncio as redis_async
        self.redis = redis_async.from_url(redis_url, decode_responses=True)
        self.rate_limiter = None
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Initialize rate limiter if not done
        if self.rate_limiter is None:
            try:
                self.rate_limiter = RateLimiter(self.redis)
                self.logger.info("Rate limiter initialized in middleware")
            except Exception as e:
                self.logger.error(f"Failed to initialize rate limiter: {e}")
                # Continue without rate limiting
                await self.app(scope, receive, send)
                return
        
        # Create request object
        from starlette.requests import Request
        request = Request(scope, receive)
        
        # Extract user information (you'll need to implement this based on your auth system)
        user_id = None
        user_role = "anonymous"
        
        # TODO: Extract user info from JWT token or session
        # For now, using anonymous user
        
        try:
            # Check rate limits
            status = await self.rate_limiter.check_rate_limit(
                request=request,
                user_id=user_id,
                user_role=user_role
            )
            
            if not status.allowed:
                # Return rate limit exceeded response
                from starlette.responses import JSONResponse
                response = JSONResponse(
                    {
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": status.retry_after
                    },
                    status_code=429,
                    headers={
                        "X-RateLimit-Remaining": str(status.requests_remaining),
                        "X-RateLimit-Reset": str(status.reset_time),
                        "Retry-After": str(status.retry_after or 60)
                    }
                )
                await response(scope, receive, send)
                return
            
        except Exception as e:
            self.logger.error(f"Rate limiting check failed: {e}")
            # Continue without rate limiting on error
        
        # Continue to the application
        await self.app(scope, receive, send)
