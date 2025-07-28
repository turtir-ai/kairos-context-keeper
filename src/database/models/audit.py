"""
Comprehensive Audit Logging System for Kairos
Tracks all user actions, security events, and system changes for compliance and security auditing.
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncpg
import logging


class AuditEventType(Enum):
    """Types of audit events that can be logged"""
    
    # Authentication events
    LOGIN_SUCCESS = "auth_login_success"
    LOGIN_FAILED = "auth_login_failed"
    LOGOUT = "auth_logout"
    PASSWORD_CHANGED = "auth_password_changed"
    PASSWORD_RESET = "auth_password_reset"
    API_KEY_CREATED = "auth_api_key_created"
    API_KEY_DELETED = "auth_api_key_deleted"
    SESSION_CREATED = "auth_session_created"
    SESSION_EXPIRED = "auth_session_expired"
    
    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_INVITED = "user_invited"
    USER_ACTIVATED = "user_activated"
    USER_SUSPENDED = "user_suspended"
    ROLE_CHANGED = "user_role_changed"
    
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    PROJECT_ROLE_CHANGED = "project_role_changed"
    
    # Task and workflow events
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_EXECUTED = "task_executed"
    TASK_CANCELLED = "task_cancelled"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_EXECUTED = "workflow_executed"
    
    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIG_CHANGED = "config_changed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    
    # Security events
    UNAUTHORIZED_ACCESS = "security_unauthorized_access"
    PERMISSION_DENIED = "security_permission_denied"
    SUSPICIOUS_ACTIVITY = "security_suspicious_activity"
    BRUTE_FORCE_ATTEMPT = "security_brute_force"
    SECURITY_ALERT = "security_alert"
    
    # Data events
    DATA_EXPORT = "data_exported"
    DATA_IMPORT = "data_imported"
    DATA_DELETED = "data_deleted"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    
    # Invitation events
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REJECTED = "invitation_rejected"
    INVITATION_EXPIRED = "invitation_expired"
    INVITATION_RESENT = "invitation_resent"
    INVITATION_CANCELLED = "invitation_cancelled"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogger:
    """Handles audit logging with comprehensive tracking and security features"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting for suspicious activities
        self.rate_limits = {
            AuditEventType.LOGIN_FAILED: {"count": 5, "window": 300},  # 5 failed logins in 5 minutes
            AuditEventType.UNAUTHORIZED_ACCESS: {"count": 10, "window": 600},  # 10 unauthorized in 10 minutes
            AuditEventType.PERMISSION_DENIED: {"count": 20, "window": 600}  # 20 permission denied in 10 minutes
        }
    
    async def initialize(self):
        """Initialize audit logging tables"""
        await self._create_audit_tables()
        await self.log_event(
            event_type=AuditEventType.SYSTEM_STARTED,
            severity=AuditSeverity.MEDIUM,
            details={"component": "audit_logger", "version": "1.0.0"}
        )
    
    async def _create_audit_tables(self):
        """Create comprehensive audit logging tables"""
        try:
            async with self.db_pool.acquire() as conn:
                # Main audit log table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        event_type VARCHAR(100) NOT NULL,
                        user_id UUID,
                        username VARCHAR(255),
                        email VARCHAR(255),
                        ip_address INET,
                        user_agent TEXT,
                        session_id VARCHAR(255),
                        project_id UUID,
                        resource_type VARCHAR(100),
                        resource_id VARCHAR(255),
                        action_details JSONB,
                        severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                        success BOOLEAN NOT NULL DEFAULT true,
                        error_message TEXT,
                        request_id VARCHAR(255),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        additional_metadata JSONB
                    );
                """)
                
                # Authentication events table (more detailed)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS auth_audit_logs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        event_type VARCHAR(50) NOT NULL,
                        user_id UUID,
                        email VARCHAR(255),
                        ip_address INET,
                        user_agent TEXT,
                        success BOOLEAN NOT NULL,
                        failure_reason VARCHAR(255),
                        session_id VARCHAR(255),
                        api_key_id UUID,
                        two_factor_used BOOLEAN DEFAULT false,
                        geo_location JSONB,
                        device_fingerprint VARCHAR(255),
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Security events table (for critical security monitoring)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_audit_logs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        event_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        user_id UUID,
                        source_ip INET,
                        target_resource VARCHAR(255),
                        threat_level INTEGER DEFAULT 1,
                        automated_response VARCHAR(100),
                        investigation_status VARCHAR(50) DEFAULT 'open',
                        details JSONB,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP WITH TIME ZONE,
                        resolved_by UUID
                    );
                """)
                
                # User invitation audit table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_invitations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email VARCHAR(255) NOT NULL,
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        role VARCHAR(50) NOT NULL,
                        invited_by UUID NOT NULL,
                        invitation_token VARCHAR(255) NOT NULL UNIQUE,
                        message TEXT,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        accepted_at TIMESTAMP WITH TIME ZONE,
                        rejected_at TIMESTAMP WITH TIME ZONE
                    );
                """)
                
                # User sessions table for session management
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL,
                        session_token VARCHAR(255) NOT NULL UNIQUE,
                        refresh_token VARCHAR(255) NOT NULL UNIQUE,
                        ip_address INET,
                        user_agent TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN DEFAULT true
                    );
                """)
                
                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp 
                    ON audit_logs(timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id 
                    ON audit_logs(user_id, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type 
                    ON audit_logs(event_type, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_logs_severity 
                    ON audit_logs(severity, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_timestamp 
                    ON auth_audit_logs(timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_ip 
                    ON auth_audit_logs(ip_address, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_security_audit_logs_severity 
                    ON security_audit_logs(severity, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
                    ON user_sessions(user_id, is_active);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_invitations_email 
                    ON user_invitations(email, status);
                """)
                
                self.logger.info("✅ Audit logging tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to create audit tables: {e}")
            raise
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: str = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        details: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None,
        session_id: str = None,
        project_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        success: bool = True,
        error_message: str = None,
        request_id: str = None
    ):
        """Log a general audit event"""
        try:
            # Get user info if user_id is provided
            username = None
            email = None
            if user_id and self.db_pool:
                async with self.db_pool.acquire() as conn:
                    user_info = await conn.fetchrow(
                        "SELECT username, email FROM users WHERE id = $1",
                        user_id
                    )
                    if user_info:
                        username = user_info['username']
                        email = user_info['email']
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_logs (
                        event_type, user_id, username, email, ip_address, user_agent,
                        session_id, project_id, resource_type, resource_id, action_details,
                        severity, success, error_message, request_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    """,
                    event_type.value, user_id, username, email, ip_address, user_agent,
                    session_id, project_id, resource_type, resource_id, json.dumps(details or {}),
                    severity.value, success, error_message, request_id
                )
            
            # Check for rate limiting patterns
            if event_type in self.rate_limits:
                await self._check_rate_limit(event_type, user_id, ip_address)
            
            self.logger.info(
                f"Audit event logged: {event_type.value} - User: {username or 'Anonymous'} - Success: {success}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event {event_type.value}: {e}")
    
    async def log_auth_event(
        self,
        action: str = None,
        event_type: AuditEventType = None,
        user_id: str = None,
        email: str = None,
        ip_address: str = None,
        user_agent: str = None,
        success: bool = True,
        failure_reason: str = None,
        session_id: str = None,
        api_key_id: str = None,
        details: Dict[str, Any] = None
    ):
        """Log authentication-specific events with enhanced details"""
        try:
            # Handle legacy 'action' parameter
            if action and not event_type:
                event_mapping = {
                    "login_success": AuditEventType.LOGIN_SUCCESS,
                    "login_failed": AuditEventType.LOGIN_FAILED,
                    "logout": AuditEventType.LOGOUT,
                    "session_created": AuditEventType.SESSION_CREATED,
                    "session_expired": AuditEventType.SESSION_EXPIRED,
                    "permission_check_error": AuditEventType.UNAUTHORIZED_ACCESS
                }
                event_type = event_mapping.get(action, AuditEventType.LOGIN_FAILED)
            
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO auth_audit_logs (
                        event_type, user_id, email, ip_address, user_agent,
                        success, failure_reason, session_id, api_key_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    event_type.value, user_id, email, ip_address, user_agent,
                    success, failure_reason, session_id, api_key_id
                )
            
            # Also log to main audit log
            await self.log_event(
                event_type=event_type,
                user_id=user_id,
                severity=AuditSeverity.HIGH if not success else AuditSeverity.LOW,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                success=success,
                error_message=failure_reason
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log auth event: {e}")
    
    async def log_security_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: str = None,
        source_ip: str = None,
        target_resource: str = None,
        threat_level: int = 1,
        details: Dict[str, Any] = None
    ):
        """Log security-specific events for threat monitoring"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO security_audit_logs (
                        event_type, severity, user_id, source_ip, target_resource,
                        threat_level, details
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    event_type.value, severity.value, user_id, source_ip,
                    target_resource, threat_level, json.dumps(details or {})
                )
            
            # Critical security events should also go to main audit log
            if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                await self.log_event(
                    event_type=event_type,
                    user_id=user_id,
                    severity=severity,
                    details=details,
                    ip_address=source_ip,
                    resource_id=target_resource,
                    success=False  # Security events are typically failures
                )
            
            self.logger.warning(
                f"Security event: {event_type.value} - Severity: {severity.value} - IP: {source_ip}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")
    
    async def _check_rate_limit(
        self,
        event_type: AuditEventType,
        user_id: str = None,
        ip_address: str = None
    ):
        """Check for suspicious rate limiting patterns"""
        try:
            rate_limit = self.rate_limits[event_type]
            window_start = datetime.utcnow() - timedelta(seconds=rate_limit["window"])
            
            async with self.db_pool.acquire() as conn:
                # Check by user_id if provided
                if user_id:
                    count = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM audit_logs 
                        WHERE event_type = $1 AND user_id = $2 AND timestamp >= $3
                        """,
                        event_type.value, user_id, window_start
                    )
                    
                    if count >= rate_limit["count"]:
                        await self.log_security_event(
                            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                            severity=AuditSeverity.HIGH,
                            user_id=user_id,
                            details={
                                "trigger_event": event_type.value,
                                "count": count,
                                "window_seconds": rate_limit["window"],
                                "threshold": rate_limit["count"]
                            }
                        )
                
                # Check by IP address if provided
                if ip_address:
                    count = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM audit_logs 
                        WHERE event_type = $1 AND ip_address = $2 AND timestamp >= $3
                        """,
                        event_type.value, ip_address, window_start
                    )
                    
                    if count >= rate_limit["count"]:
                        await self.log_security_event(
                            event_type=AuditEventType.BRUTE_FORCE_ATTEMPT,
                            severity=AuditSeverity.CRITICAL,
                            source_ip=ip_address,
                            details={
                                "trigger_event": event_type.value,
                                "count": count,
                                "window_seconds": rate_limit["window"],
                                "threshold": rate_limit["count"]
                            }
                        )
                        
        except Exception as e:
            self.logger.error(f"Failed to check rate limit: {e}")
    
    async def get_audit_logs(
        self,
        user_id: str = None,
        event_type: AuditEventType = None,
        severity: AuditSeverity = None,
        start_date: datetime = None,
        end_date: datetime = None,
        success_filter: bool = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs with filtering options"""
        try:
            # Build query conditions
            conditions = []
            params = []
            param_count = 1
            
            if user_id:
                conditions.append(f"user_id = ${param_count}")
                params.append(user_id)
                param_count += 1
            
            if event_type:
                conditions.append(f"event_type = ${param_count}")
                params.append(event_type.value)
                param_count += 1
            
            if severity:
                conditions.append(f"severity = ${param_count}")
                params.append(severity.value)
                param_count += 1
            
            if start_date:
                conditions.append(f"timestamp >= ${param_count}")
                params.append(start_date)
                param_count += 1
            
            if end_date:
                conditions.append(f"timestamp <= ${param_count}")
                params.append(end_date)
                param_count += 1
            
            if success_filter is not None:
                conditions.append(f"success = ${param_count}")
                params.append(success_filter)
                param_count += 1
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            params.extend([limit, offset])
            
            query = f"""
                SELECT * FROM audit_logs 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get audit logs: {e}")
            return []
    
    async def get_security_alerts(
        self,
        severity: AuditSeverity = None,
        unresolved_only: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get security alerts for monitoring dashboard"""
        try:
            conditions = []
            params = []
            param_count = 1
            
            if severity:
                conditions.append(f"severity = ${param_count}")
                params.append(severity.value)
                param_count += 1
            
            if unresolved_only:
                conditions.append("resolved_at IS NULL")
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params.append(limit)
            
            query = f"""
                SELECT * FROM security_audit_logs 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ${param_count}
            """
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get security alerts: {e}")
            return []
    
    async def resolve_security_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_notes: str = None
    ):
        """Mark a security alert as resolved"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE security_audit_logs 
                    SET resolved_at = CURRENT_TIMESTAMP, 
                        resolved_by = $1, 
                        investigation_status = 'resolved'
                    WHERE id = $2
                    """,
                    resolved_by, alert_id
                )
            
            await self.log_event(
                event_type=AuditEventType.SECURITY_ALERT,
                user_id=resolved_by,
                severity=AuditSeverity.MEDIUM,
                details={
                    "action": "alert_resolved",
                    "alert_id": alert_id,
                    "resolution_notes": resolution_notes
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to resolve security alert: {e}")
    
    async def cleanup_old_logs(self, retention_days: int = 365):
        """Clean up old audit logs based on retention policy"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            async with self.db_pool.acquire() as conn:
                # Archive critical events longer, delete others
                deleted_count = await conn.fetchval(
                    """
                    DELETE FROM audit_logs 
                    WHERE timestamp < $1 AND severity NOT IN ('high', 'critical')
                    """,
                    cutoff_date
                )
                
                # Clean up auth logs (shorter retention)
                auth_cutoff = datetime.utcnow() - timedelta(days=retention_days // 2)
                auth_deleted = await conn.fetchval(
                    """
                    DELETE FROM auth_audit_logs 
                    WHERE timestamp < $1 AND success = true
                    """,
                    auth_cutoff
                )
            
            await self.log_event(
                event_type=AuditEventType.SYSTEM_STARTED,  # Use existing enum
                severity=AuditSeverity.LOW,
                details={
                    "action": "log_cleanup",
                    "audit_logs_deleted": deleted_count,
                    "auth_logs_deleted": auth_deleted,
                    "retention_days": retention_days
                }
            )
            
            self.logger.info(f"Cleaned up {deleted_count} audit logs and {auth_deleted} auth logs")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")

"""
Audit logging models for Kairos security and compliance
"""

import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class AuditEventType(Enum):
    """Types of auditable events"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    API_KEY_CREATED = "api_key_created"
    API_KEY_DELETED = "api_key_deleted"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_SUSPENDED = "user_suspended"
    USER_ACTIVATED = "user_activated"
    
    # Project management
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    PROJECT_ROLE_CHANGED = "project_role_changed"
    
    # Invitation events
    USER_INVITED = "user_invited"
    INVITATION_RESENT = "invitation_resent"
    INVITATION_CANCELLED = "invitation_cancelled"
    INVITATION_ACCEPTED = "invitation_accepted"
    
    # System operations
    MODEL_ACCESSED = "model_accessed"
    LLM_REQUEST = "llm_request"
    BUDGET_EXCEEDED = "budget_exceeded"
    ANOMALY_DETECTED = "anomaly_detected"
    SYSTEM_ERROR = "system_error"
    
    # Data operations
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    
    # Security events
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONFIGURATION_CHANGED = "configuration_changed"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLogger:
    """Audit logging service for compliance and security monitoring"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """Log an audit event"""
        audit_id = str(uuid.uuid4())
        
        # Sanitize details to remove sensitive information
        sanitized_details = self._sanitize_details(details or {})
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs (
                    id, event_type, user_id, project_id, severity,
                    resource_type, resource_id, details, ip_address,
                    user_agent, success, error_message, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, CURRENT_TIMESTAMP)
                """,
                audit_id, event_type.value, user_id, project_id, severity.value,
                resource_type, resource_id, json.dumps(sanitized_details),
                ip_address, user_agent, success, error_message
            )
        
        return audit_id
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs with filtering"""
        where_clauses = []
        params = []
        param_count = 1
        
        if user_id:
            where_clauses.append(f"user_id = ${param_count}")
            params.append(user_id)
            param_count += 1
        
        if project_id:
            where_clauses.append(f"project_id = ${param_count}")
            params.append(project_id)
            param_count += 1
        
        if event_type:
            where_clauses.append(f"event_type = ${param_count}")
            params.append(event_type.value)
            param_count += 1
        
        if severity:
            where_clauses.append(f"severity = ${param_count}")
            params.append(severity.value)
            param_count += 1
        
        if start_date:
            where_clauses.append(f"timestamp >= ${param_count}")
            params.append(start_date)
            param_count += 1
        
        if end_date:
            where_clauses.append(f"timestamp <= ${param_count}")
            params.append(end_date)
            param_count += 1
        
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        params.extend([limit, offset])
        
        query = f"""
            SELECT al.*, u.username, u.email, p.name as project_name
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            LEFT JOIN projects p ON al.project_id = p.id
            {where_clause}
            ORDER BY al.timestamp DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "project_id": row["project_id"],
                    "project_name": row["project_name"],
                    "severity": row["severity"],
                    "resource_type": row["resource_type"],
                    "resource_id": row["resource_id"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "ip_address": row["ip_address"],
                    "user_agent": row["user_agent"],
                    "success": row["success"],
                    "error_message": row["error_message"],
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in rows
            ]
    
    async def get_security_alerts(
        self,
        hours_back: int = 24,
        min_severity: AuditSeverity = AuditSeverity.HIGH
    ) -> List[Dict[str, Any]]:
        """Get recent security alerts"""
        severity_levels = {
            AuditSeverity.LOW: 1,
            AuditSeverity.MEDIUM: 2,
            AuditSeverity.HIGH: 3,
            AuditSeverity.CRITICAL: 4
        }
        
        min_level = severity_levels[min_severity]
        since_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT al.*, u.username, u.email, p.name as project_name
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                LEFT JOIN projects p ON al.project_id = p.id
                WHERE al.timestamp >= $1
                AND CASE 
                    WHEN al.severity = 'low' THEN 1
                    WHEN al.severity = 'medium' THEN 2
                    WHEN al.severity = 'high' THEN 3
                    WHEN al.severity = 'critical' THEN 4
                    ELSE 0
                END >= $2
                AND (al.success = FALSE OR al.event_type IN (
                    'permission_denied', 'rate_limit_exceeded', 
                    'suspicious_activity', 'anomaly_detected'
                ))
                ORDER BY al.timestamp DESC
                LIMIT 100
                """,
                since_time, min_level
            )
            
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "project_id": row["project_id"],
                    "project_name": row["project_name"],
                    "severity": row["severity"],
                    "resource_type": row["resource_type"],
                    "resource_id": row["resource_id"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "ip_address": row["ip_address"],
                    "user_agent": row["user_agent"],
                    "success": row["success"],
                    "error_message": row["error_message"],
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in rows
            ]
    
    async def get_user_activity_summary(
        self,
        user_id: str,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get activity summary for a user"""
        since_date = datetime.utcnow() - timedelta(days=days_back)
        
        async with self.db_pool.acquire() as conn:
            # Total events
            total_events = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_logs 
                WHERE user_id = $1 AND timestamp >= $2
                """,
                user_id, since_date
            )
            
            # Events by type
            event_types = await conn.fetch(
                """
                SELECT event_type, COUNT(*) as count
                FROM audit_logs
                WHERE user_id = $1 AND timestamp >= $2
                GROUP BY event_type
                ORDER BY count DESC
                """,
                user_id, since_date
            )
            
            # Failed operations
            failed_ops = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_logs
                WHERE user_id = $1 AND timestamp >= $2 AND success = FALSE
                """,
                user_id, since_date
            )
            
            # Security events
            security_events = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_logs
                WHERE user_id = $1 AND timestamp >= $2
                AND event_type IN ('permission_denied', 'rate_limit_exceeded', 'suspicious_activity')
                """,
                user_id, since_date
            )
            
            return {
                "user_id": user_id,
                "period_days": days_back,
                "total_events": total_events,
                "failed_operations": failed_ops,
                "security_events": security_events,
                "event_types": [
                    {"type": row["event_type"], "count": row["count"]}
                    for row in event_types
                ]
            }
    
    async def cleanup_old_logs(self, days_to_keep: int = 365) -> int:
        """Clean up old audit logs to manage storage"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """DELETE FROM audit_logs WHERE timestamp < $1""",
                cutoff_date
            )
            
            # Extract number of deleted rows from result
            return int(result.split()[-1]) if result else 0
    
    async def log_auth_event(
        self,
        user_id: Optional[str] = None,
        action: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """Legacy method for logging authentication events"""
        # Map legacy action names to new event types
        action_mapping = {
            'login_success': AuditEventType.LOGIN_SUCCESS,
            'login_failed': AuditEventType.LOGIN_FAILED,
            'logout': AuditEventType.LOGOUT,
            'user_registered': AuditEventType.USER_CREATED,
            'session_created': AuditEventType.LOGIN_SUCCESS,
            'session_invalidated': AuditEventType.LOGOUT,
            'permission_check_error': AuditEventType.SYSTEM_ERROR
        }
        
        event_type = action_mapping.get(action, AuditEventType.SYSTEM_ERROR)
        severity = AuditSeverity.HIGH if not success else AuditSeverity.MEDIUM
        
        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            severity=severity,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from audit details"""
        sensitive_keys = {
            'password', 'password_hash', 'api_key', 'secret', 'token',
            'auth_token', 'access_token', 'refresh_token', 'private_key',
            'credit_card', 'ssn', 'social_security'
        }
        
        sanitized = {}
        for key, value in details.items():
            # Convert key to lowercase for comparison
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_details(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_details(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized


# Helper functions for common audit operations
async def log_auth_event(
    audit_logger: AuditLogger,
    event_type: AuditEventType,
    user_id: Optional[str] = None,
    success: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
    details: Optional[Dict] = None
):
    """Log authentication-related event"""
    severity = AuditSeverity.HIGH if not success else AuditSeverity.MEDIUM
    
    await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message,
        details=details
    )


async def log_permission_denied(
    audit_logger: AuditLogger,
    user_id: str,
    resource_type: str,
    resource_id: str,
    required_permission: str,
    project_id: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """Log permission denied event"""
    await audit_logger.log_event(
        event_type=AuditEventType.PERMISSION_DENIED,
        user_id=user_id,
        project_id=project_id,
        severity=AuditSeverity.HIGH,
        resource_type=resource_type,
        resource_id=resource_id,
        success=False,
        ip_address=ip_address,
        details={
            "required_permission": required_permission,
            "action_attempted": "access_denied"
        }
    )


async def log_data_access(
    audit_logger: AuditLogger,
    user_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    project_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None
):
    """Log data access event"""
    event_type = AuditEventType.DATA_ACCESSED
    if action in ["modify", "update", "create"]:
        event_type = AuditEventType.DATA_MODIFIED
    elif action == "delete":
        event_type = AuditEventType.DATA_DELETED
    elif action == "export":
        event_type = AuditEventType.DATA_EXPORTED
    
    await audit_logger.log_event(
        event_type=event_type,
        user_id=user_id,
        project_id=project_id,
        severity=AuditSeverity.MEDIUM,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details={
            "action": action,
            **(details or {})
        }
    )
