#!/usr/bin/env python3
"""
Kairos: The Context Keeper - Configuration Settings
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "postgresql://kairos_user:secure_password@localhost:5432/kairos_db"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
    "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
}

# Redis Configuration (for rate limiting and caching)
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD"),
    "decode_responses": True,
}

# Rate Limiting Configuration
RATE_LIMIT_CONFIG = {
    "default_strategy": "sliding_window",
    "redis_config": REDIS_CONFIG,
    "user_limits": {
        "admin": {"requests": 1000, "window": 3600},  # 1000 requests per hour
        "premium": {"requests": 500, "window": 3600},  # 500 requests per hour
        "basic": {"requests": 100, "window": 3600},    # 100 requests per hour
        "trial": {"requests": 50, "window": 3600},     # 50 requests per hour
    },
    "endpoint_limits": {
        "/ai/generate": {"requests": 10, "window": 60},    # 10 AI requests per minute
        "/api/memory/query": {"requests": 50, "window": 60}, # 50 memory queries per minute
        "/api/orchestration/tasks": {"requests": 20, "window": 60}, # 20 task operations per minute
    },
    "ip_limits": {
        "requests": 200,
        "window": 3600,  # 200 requests per hour per IP
    },
    "whitelist_ips": [
        "127.0.0.1",
        "::1",
        "localhost",
    ],
    "suspicious_threshold": 10,  # Flag IP as suspicious after 10 violations
}

# RBAC Configuration
RBAC_CONFIG = {
    "roles": {
        "admin": {
            "permissions": ["*"],  # All permissions
            "description": "Full system access"
        },
        "premium": {
            "permissions": [
                "read:memory", "write:memory",
                "read:tasks", "write:tasks",
                "read:agents", "control:agents",
                "read:monitoring", "export:data"
            ],
            "description": "Premium user access"
        },
        "basic": {
            "permissions": [
                "read:memory", "read:tasks",
                "read:agents", "read:monitoring"
            ],
            "description": "Basic user access"
        },
        "trial": {
            "permissions": [
                "read:memory", "read:tasks"
            ],
            "description": "Trial user access"
        }
    },
    "default_role": "trial",
    "session_timeout": 3600,  # 1 hour
}

# Audit Logging Configuration
AUDIT_CONFIG = {
    "log_level": os.getenv("AUDIT_LOG_LEVEL", "INFO"),
    "log_file": os.getenv("AUDIT_LOG_FILE", "logs/audit.log"),
    "max_file_size": int(os.getenv("AUDIT_MAX_FILE_SIZE", "10485760")),  # 10MB
    "backup_count": int(os.getenv("AUDIT_BACKUP_COUNT", "5")),
    "events_to_log": [
        "user_login", "user_logout", "permission_denied",
        "rate_limit_exceeded", "suspicious_activity",
        "admin_action", "data_access", "system_change"
    ],
    "sensitive_fields": ["password", "token", "api_key", "secret"],
    "retention_days": int(os.getenv("AUDIT_RETENTION_DAYS", "90")),
}

# Security Configuration
SECURITY_CONFIG = {
    "jwt_secret": os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production"),
    "jwt_algorithm": "HS256",
    "jwt_expire_hours": int(os.getenv("JWT_EXPIRE_HOURS", "24")),
    "password_min_length": 8,
    "password_require_special": True,
    "max_login_attempts": 5,
    "lockout_duration": 900,  # 15 minutes
}

# Monitoring Configuration
MONITORING_CONFIG = {
    "metrics_retention_hours": int(os.getenv("METRICS_RETENTION_HOURS", "168")),  # 7 days
    "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),  # 30 seconds
    "alert_thresholds": {
        "cpu_usage": 80,
        "memory_usage": 85,
        "disk_usage": 90,
        "response_time_ms": 1000,
    },
}

# Application Configuration
APP_CONFIG = {
    "title": "Kairos: The Context Keeper",
    "version": "1.0.0",
    "description": "Autonomous development supervisor powered by context engineering",
    "debug": os.getenv("DEBUG", "false").lower() == "true",
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "8000")),
    "cors_origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
}

# Ollama Configuration
OLLAMA_CONFIG = {
    "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "timeout": int(os.getenv("OLLAMA_TIMEOUT", "60")),
    "default_model": os.getenv("OLLAMA_DEFAULT_MODEL", "deepseek-r1:8b"),
    "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2048")),
}

# Neo4j Configuration (for advanced memory systems)
NEO4J_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "password"),
    "database": os.getenv("NEO4J_DATABASE", "kairos"),
}

# Environment-specific configurations
def get_config() -> Dict[str, Any]:
    """Get configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    config = {
        "database": DATABASE_CONFIG,
        "redis": REDIS_CONFIG,
        "rate_limit": RATE_LIMIT_CONFIG,
        "rbac": RBAC_CONFIG,
        "audit": AUDIT_CONFIG,
        "security": SECURITY_CONFIG,
        "monitoring": MONITORING_CONFIG,
        "app": APP_CONFIG,
        "ollama": OLLAMA_CONFIG,
        "neo4j": NEO4J_CONFIG,
        "environment": env,
    }
    
    # Environment-specific overrides
    if env == "production":
        config["app"]["debug"] = False
        config["security"]["jwt_expire_hours"] = 8
        config["rate_limit"]["user_limits"]["trial"]["requests"] = 25  # Stricter in prod
        config["audit"]["log_level"] = "WARNING"
    elif env == "testing":
        config["database"]["url"] = "sqlite:///test_kairos.db"
        config["redis"]["db"] = 1  # Use different Redis DB for tests
        config["rate_limit"]["user_limits"]["basic"]["requests"] = 1000  # Relaxed for tests
    
    return config

# Global configuration instance
CONFIG = get_config()

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Validate required settings
    if not CONFIG["security"]["jwt_secret"] or CONFIG["security"]["jwt_secret"] == "your-super-secret-jwt-key-change-in-production":
        if CONFIG["environment"] == "production":
            errors.append("JWT_SECRET must be set in production")
    
    if CONFIG["app"]["debug"] and CONFIG["environment"] == "production":
        errors.append("Debug mode should not be enabled in production")
    
    # Validate rate limits
    for role, limits in CONFIG["rate_limit"]["user_limits"].items():
        if limits["requests"] <= 0 or limits["window"] <= 0:
            errors.append(f"Invalid rate limits for role {role}")
    
    # Validate RBAC roles
    if "admin" not in CONFIG["rbac"]["roles"]:
        errors.append("Admin role must be defined in RBAC configuration")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

# Validate configuration on import
validate_config()
