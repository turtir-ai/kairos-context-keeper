-- Migration: Multi-user RBAC support
-- Purpose: Add users, API keys, and audit logging tables for enterprise multi-user functionality

-- Users table with role-based access control
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name VARCHAR(100) DEFAULT '',
    last_name VARCHAR(100) DEFAULT '',
    role VARCHAR(50) NOT NULL DEFAULT 'user', -- super_admin, admin, user, viewer
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, inactive, suspended, pending, deleted
    profile_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT NULL
);

-- API keys table for user authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '["read", "write"]',
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT NULL
);

-- Audit logs table for compliance and security monitoring
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) REFERENCES users(id) ON DELETE SET NULL,
    project_id VARCHAR(255) REFERENCES projects(id) ON DELETE SET NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_project_id ON audit_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_severity ON audit_logs(severity);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_success ON audit_logs(success);

-- Update projects table to link with users
ALTER TABLE projects ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(255) REFERENCES users(id);

-- Update project_members to have proper foreign key
DO $$ 
BEGIN
    -- Add foreign key constraint if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_project_members_user') THEN
        ALTER TABLE project_members 
        ADD CONSTRAINT fk_project_members_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Enhanced project access function with proper user validation
CREATE OR REPLACE FUNCTION has_project_access_v2(
    p_user_id VARCHAR,
    p_project_id VARCHAR,
    p_required_role VARCHAR DEFAULT 'member'
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_role VARCHAR;
    v_user_system_role VARCHAR;
    v_role_hierarchy JSONB := '{"viewer": 1, "member": 2, "admin": 3, "owner": 4}';
    v_system_role_hierarchy JSONB := '{"viewer": 1, "user": 2, "admin": 3, "super_admin": 4}';
BEGIN
    -- Check if user exists and is active
    SELECT role INTO v_user_system_role
    FROM users
    WHERE id = p_user_id AND status = 'active';
    
    IF v_user_system_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Super admin has access to everything
    IF v_user_system_role = 'super_admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Get user's role in project
    SELECT role INTO v_user_role
    FROM project_members
    WHERE user_id = p_user_id AND project_id = p_project_id;
    
    IF v_user_role IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check role hierarchy
    RETURN (v_role_hierarchy->v_user_role)::INTEGER >= (v_role_hierarchy->p_required_role)::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- User management functions
CREATE OR REPLACE FUNCTION get_user_projects_v2(p_user_id VARCHAR)
RETURNS TABLE (
    project_id VARCHAR,
    project_name VARCHAR,
    project_description TEXT,
    user_role VARCHAR,
    joined_at TIMESTAMP,
    project_created_at TIMESTAMP,
    project_settings JSONB,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.description,
        pm.role,
        pm.joined_at,
        p.created_at,
        COALESCE(p.settings::JSONB, '{}'::JSONB),
        p.is_active
    FROM projects p
    JOIN project_members pm ON p.id = pm.project_id
    WHERE pm.user_id = p_user_id
    AND p.is_active = TRUE
    ORDER BY pm.joined_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Audit log cleanup function
CREATE OR REPLACE FUNCTION cleanup_audit_logs(days_to_keep INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create system user for migrations and system operations
INSERT INTO users (
    id, email, username, password_hash, first_name, last_name, 
    role, status
) VALUES (
    'system', 'system@kairos.local', 'system', 
    'locked', 'System', 'User', 'super_admin', 'active'
) ON CONFLICT (id) DO NOTHING;

-- Link existing projects to system user if no owner is set
UPDATE projects 
SET owner_user_id = 'system' 
WHERE owner_user_id IS NULL;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    -- Add trigger for users table if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Add budget tracking tables project-specific columns if they don't exist
ALTER TABLE budget_usage ADD COLUMN IF NOT EXISTS user_id VARCHAR(255) REFERENCES users(id);
ALTER TABLE workflow_patterns ADD COLUMN IF NOT EXISTS user_id VARCHAR(255) REFERENCES users(id);
ALTER TABLE anomaly_alerts ADD COLUMN IF NOT EXISTS user_id VARCHAR(255) REFERENCES users(id);

-- Add indexes for new user_id columns
CREATE INDEX IF NOT EXISTS idx_budget_usage_user_id ON budget_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_patterns_user_id ON workflow_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_user_id ON anomaly_alerts(user_id);

-- Grant necessary permissions (adjust based on your database setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kairos_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO kairos_user;
