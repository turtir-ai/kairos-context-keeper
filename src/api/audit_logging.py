"""
Audit Logging System for Kairos
Provides comprehensive audit logging for security, compliance, and monitoring.
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import Request
import hashlib
import os


class AuditEventType(Enum):
    """Types of audit events"""
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    API_CALL = "api_call"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SECURITY_VIOLATION = "security_violation"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: str
    user_agent: Optional[str]
    endpoint: str
    method: str
    status_code: int
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    event_id: str


class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, log_file: str = "logs/audit.log"):
        self.log_file = log_file
        self.logger = logging.getLogger("kairos.audit")
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure file handler for audit logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        
        # Rate limiting for similar events
        self.event_cache = {}
        self.cache_size = 1000
        
        self.logger.info("🔍 Audit logging system initialized")
    
    def generate_event_id(self, event_data: str) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now().isoformat()
        combined = f"{timestamp}:{event_data}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        request: Optional[Request] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 200
    ):
        """Log an audit event"""
        try:
            # Extract request information
            ip_address = "unknown"
            user_agent = None
            endpoint = "unknown"
            method = "unknown"
            
            if request:
                ip_address = self._get_client_ip(request)
                user_agent = request.headers.get("user-agent")
                endpoint = str(request.url.path)
                method = request.method
            
            # Create audit event
            event = AuditEvent(
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                message=message,
                details=details or {},
                timestamp=datetime.now(),
                event_id=self.generate_event_id(f"{event_type.value}:{ip_address}:{endpoint}")
            )
            
            # Check rate limiting for similar events
            if not self._should_log_event(event):
                return
            
            # Log the event
            event_json = json.dumps(asdict(event), default=str)
            self.logger.info(event_json)
            
            # Store in cache for rate limiting
            cache_key = f"{event_type.value}:{ip_address}:{endpoint}"
            self.event_cache[cache_key] = datetime.now()
            
            # Clean cache if too large
            if len(self.event_cache) > self.cache_size:
                self._clean_cache()
                
        except Exception as e:
            # Use standard logger for audit system errors
            logging.error(f"Audit logging failed: {e}")
    
    def _should_log_event(self, event: AuditEvent) -> bool:
        """Check if event should be logged (rate limiting)"""
        cache_key = f"{event.event_type.value}:{event.ip_address}:{event.endpoint}"
        
        if cache_key in self.event_cache:
            last_logged = self.event_cache[cache_key]
            time_diff = (datetime.now() - last_logged).total_seconds()
            
            # Rate limit based on severity
            min_interval = {
                AuditSeverity.LOW: 60,      # 1 minute
                AuditSeverity.MEDIUM: 30,   # 30 seconds
                AuditSeverity.HIGH: 10,     # 10 seconds
                AuditSeverity.CRITICAL: 1   # 1 second
            }
            
            return time_diff >= min_interval.get(event.severity, 60)
        
        return True
    
    def _clean_cache(self):
        """Clean old entries from cache"""
        current_time = datetime.now()
        to_remove = []
        
        for key, timestamp in self.event_cache.items():
            if (current_time - timestamp).total_seconds() > 3600:  # 1 hour
                to_remove.append(key)
        
        for key in to_remove:
            del self.event_cache[key]
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded IP first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def log_auth_success(self, request: Request, user_id: str, session_id: str):
        """Log successful authentication"""
        await self.log_event(
            AuditEventType.AUTH_LOGIN,
            AuditSeverity.MEDIUM,
            f"User {user_id} successfully logged in",
            request=request,
            user_id=user_id,
            session_id=session_id,
            details={"login_method": "password"}
        )
    
    async def log_auth_failure(self, request: Request, attempted_user: str, reason: str):
        """Log failed authentication attempt"""
        await self.log_event(
            AuditEventType.AUTH_FAILED,
            AuditSeverity.HIGH,
            f"Failed login attempt for user: {attempted_user}",
            request=request,
            details={"attempted_user": attempted_user, "failure_reason": reason},
            status_code=401
        )
    
    async def log_permission_denied(self, request: Request, user_id: str, required_permission: str):
        """Log permission denied event"""
        await self.log_event(
            AuditEventType.PERMISSION_DENIED,
            AuditSeverity.HIGH,
            f"Permission denied for user {user_id}: {required_permission}",
            request=request,
            user_id=user_id,
            details={"required_permission": required_permission},
            status_code=403
        )
    
    async def log_rate_limit_hit(self, request: Request, user_id: Optional[str], limit_type: str):
        """Log rate limit violation"""
        await self.log_event(
            AuditEventType.RATE_LIMIT_HIT,
            AuditSeverity.MEDIUM,
            f"Rate limit exceeded: {limit_type}",
            request=request,
            user_id=user_id,
            details={"limit_type": limit_type},
            status_code=429
        )
    
    async def log_data_access(self, request: Request, user_id: str, resource: str, action: str):
        """Log data access event"""
        await self.log_event(
            AuditEventType.DATA_ACCESS,
            AuditSeverity.LOW,
            f"User {user_id} accessed {resource}",
            request=request,
            user_id=user_id,
            details={"resource": resource, "action": action}
        )
    
    async def log_security_violation(self, request: Request, violation_type: str, details: Dict[str, Any]):
        """Log security violation"""
        await self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            AuditSeverity.CRITICAL,
            f"Security violation detected: {violation_type}",
            request=request,
            details=details,
            status_code=403
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def configure_audit_logging(log_file: str = "logs/audit.log") -> AuditLogger:
    """Configure and return global audit logger"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(log_file)
    return _audit_logger


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = configure_audit_logging()
    return _audit_logger


# Convenience functions for common audit events
async def audit_login_success(request: Request, user_id: str, session_id: str):
    """Audit successful login"""
    logger = get_audit_logger()
    await logger.log_auth_success(request, user_id, session_id)


async def audit_login_failure(request: Request, attempted_user: str, reason: str):
    """Audit failed login attempt"""
    logger = get_audit_logger()
    await logger.log_auth_failure(request, attempted_user, reason)


async def audit_permission_denied(request: Request, user_id: str, required_permission: str):
    """Audit permission denied"""
    logger = get_audit_logger()
    await logger.log_permission_denied(request, user_id, required_permission)


async def audit_rate_limit_hit(request: Request, user_id: Optional[str], limit_type: str):
    """Audit rate limit hit"""
    logger = get_audit_logger()
    await logger.log_rate_limit_hit(request, user_id, limit_type)


async def audit_data_access(request: Request, user_id: str, resource: str, action: str):
    """Audit data access"""
    logger = get_audit_logger()
    await logger.log_data_access(request, user_id, resource, action)


async def audit_security_violation(request: Request, violation_type: str, details: Dict[str, Any]):
    """Audit security violation"""
    logger = get_audit_logger()
    await logger.log_security_violation(request, violation_type, details)
