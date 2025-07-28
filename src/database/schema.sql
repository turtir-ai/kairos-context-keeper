-- Kairos Multi-User RBAC Database Schema
-- This schema supports complete multi-user functionality with role-based access control

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table with comprehensive profile and role management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) DEFAULT '',
    last_name VARCHAR(100) DEFAULT '',
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('super_admin', 'admin', 'user', 'viewer')),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'pending', 'deleted')),
    profile_data JSONB DEFAULT '{}',
    email_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP
);

-- Projects table for multi-project support
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    visibility VARCHAR(50) DEFAULT 'private' CHECK (visibility IN ('public', 'private', 'internal')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project members with role-based permissions
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    permissions JSONB DEFAULT '{}',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by UUID REFERENCES users(id),
    invitation_accepted BOOLEAN DEFAULT TRUE,
    UNIQUE(project_id, user_id)
);

-- API Keys for programmatic access
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]',
    scopes JSONB DEFAULT '[]',
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

-- User sessions for web authentication
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Comprehensive audit logging
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Existing tables for fine-tuning and metrics (keeping them)
CREATE TABLE IF NOT EXISTS fine_tuning_dataset (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    prompt TEXT NOT NULL,
    failed_output TEXT,
    corrected_output TEXT,
    failure_reason VARCHAR(100),
    guardian_feedback TEXT,
    error_details TEXT,
    model_key VARCHAR(255),
    task_type VARCHAR(100),
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_performance_metrics (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    model_key VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    execution_time_ms INTEGER,
    success BOOLEAN,
    token_count INTEGER,
    cost_estimate DECIMAL(10, 6),
    error_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_active ON projects(is_active);
CREATE INDEX idx_project_members_user ON project_members(user_id);
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_active ON user_sessions(is_active);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_project ON audit_logs(project_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_fine_tuning_project ON fine_tuning_dataset(project_id);
CREATE INDEX idx_performance_user ON model_performance_metrics(user_id);
CREATE INDEX idx_performance_project ON model_performance_metrics(project_id);

-- Create functions for permission checking
CREATE OR REPLACE FUNCTION has_project_access(
    user_id_param UUID,
    project_id_param UUID,
    required_role_param VARCHAR DEFAULT 'member'
) RETURNS BOOLEAN AS $$
DECLARE
    user_role VARCHAR;
    role_hierarchy INTEGER;
    required_hierarchy INTEGER;
BEGIN
    -- Get user's role in the project
    SELECT pm.role INTO user_role
    FROM project_members pm
    WHERE pm.user_id = user_id_param 
    AND pm.project_id = project_id_param;
    
    -- If user is not a member, check if they're a system admin
    IF user_role IS NULL THEN
        SELECT u.role INTO user_role
        FROM users u
        WHERE u.id = user_id_param;
        
        -- Super admin has access to everything
        IF user_role = 'super_admin' THEN
            RETURN TRUE;
        END IF;
        
        RETURN FALSE;
    END IF;
    
    -- Define role hierarchy (higher number = more permissions)
    CASE user_role
        WHEN 'owner' THEN role_hierarchy := 4;
        WHEN 'admin' THEN role_hierarchy := 3;
        WHEN 'member' THEN role_hierarchy := 2;
        WHEN 'viewer' THEN role_hierarchy := 1;
        ELSE role_hierarchy := 0;
    END CASE;
    
    CASE required_role_param
        WHEN 'owner' THEN required_hierarchy := 4;
        WHEN 'admin' THEN required_hierarchy := 3;
        WHEN 'member' THEN required_hierarchy := 2;
        WHEN 'viewer' THEN required_hierarchy := 1;
        ELSE required_hierarchy := 1;
    END CASE;
    
    RETURN role_hierarchy >= required_hierarchy;
END;
$$ LANGUAGE plpgsql;

-- Create function for user creation with default project
CREATE OR REPLACE FUNCTION create_user_with_default_project(
    email_param VARCHAR,
    username_param VARCHAR,
    password_hash_param VARCHAR,
    first_name_param VARCHAR DEFAULT '',
    last_name_param VARCHAR DEFAULT ''
) RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
    default_project_id UUID;
BEGIN
    -- Create user
    INSERT INTO users (email, username, password_hash, first_name, last_name)
    VALUES (email_param, username_param, password_hash_param, first_name_param, last_name_param)
    RETURNING id INTO new_user_id;
    
    -- Create default project for user
    INSERT INTO projects (name, description, owner_id)
    VALUES (
        'Default Project - ' || username_param,
        'Default project for ' || first_name_param || ' ' || last_name_param,
        new_user_id
    )
    RETURNING id INTO default_project_id;
    
    -- Add user as project owner
    INSERT INTO project_members (project_id, user_id, role)
    VALUES (default_project_id, new_user_id, 'owner');
    
    RETURN new_user_id;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
-- Password hash for 'admin123' using PBKDF2-SHA256
INSERT INTO users (
    id,
    email, 
    username, 
    password_hash, 
    first_name, 
    last_name, 
    role, 
    status,
    email_verified
) VALUES (
    uuid_generate_v4(),
    'admin@kairos.dev',
    'admin',
    'a1b2c3d4e5f6:d4e5f6a1b2c3a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
    'System',
    'Administrator',
    'super_admin',
    'active',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Create default demo project
INSERT INTO projects (
    id,
    name,
    description,
    owner_id,
    visibility
) VALUES (
    uuid_generate_v4(),
    'Demo Project',
    'Default demonstration project for Kairos',
    (SELECT id FROM users WHERE email = 'admin@kairos.dev'),
    'public'
) ON CONFLICT DO NOTHING;

-- Add admin to demo project
INSERT INTO project_members (
    project_id,
    user_id,
    role
) VALUES (
    (SELECT id FROM projects WHERE name = 'Demo Project'),
    (SELECT id FROM users WHERE email = 'admin@kairos.dev'),
    'owner'
) ON CONFLICT (project_id, user_id) DO NOTHING;

COMMIT;
