-- Migration: Add project_id support for multi-tenancy
-- Purpose: Enable multiple isolated projects within Kairos

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- Create project members table
CREATE TABLE IF NOT EXISTS project_members (
    project_id VARCHAR(255) REFERENCES projects(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, member, viewer
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);

-- Add project_id to existing tables
ALTER TABLE model_performance_metrics 
    ADD COLUMN IF NOT EXISTS project_id VARCHAR(255);

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_metrics_project') THEN
        ALTER TABLE model_performance_metrics 
        ADD CONSTRAINT fk_metrics_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE fine_tuning_dataset 
    ADD COLUMN IF NOT EXISTS project_id VARCHAR(255);

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_finetuning_project') THEN
        ALTER TABLE fine_tuning_dataset 
        ADD CONSTRAINT fk_finetuning_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE llm_response_cache 
    ADD COLUMN IF NOT EXISTS project_id VARCHAR(255);

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cache_project') THEN
        ALTER TABLE llm_response_cache 
        ADD CONSTRAINT fk_cache_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes for project_id
CREATE INDEX IF NOT EXISTS idx_metrics_project_id ON model_performance_metrics(project_id);
CREATE INDEX IF NOT EXISTS idx_finetuning_project_id ON fine_tuning_dataset(project_id);
CREATE INDEX IF NOT EXISTS idx_cache_project_id ON llm_response_cache(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id);

-- Function to get user's projects
CREATE OR REPLACE FUNCTION get_user_projects(p_user_id VARCHAR)
RETURNS TABLE (
    project_id VARCHAR,
    project_name VARCHAR,
    role VARCHAR,
    joined_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        pm.role,
        pm.joined_at
    FROM projects p
    JOIN project_members pm ON p.id = pm.project_id
    WHERE pm.user_id = p_user_id
    AND p.is_active = TRUE
    ORDER BY pm.joined_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to check project access
CREATE OR REPLACE FUNCTION has_project_access(
    p_user_id VARCHAR,
    p_project_id VARCHAR,
    p_required_role VARCHAR DEFAULT 'member'
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_role VARCHAR;
    v_role_hierarchy JSONB := '{"viewer": 1, "member": 2, "admin": 3, "owner": 4}';
BEGIN
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

-- Create default project for existing data
INSERT INTO projects (id, name, description, owner_id)
VALUES ('default', 'Default Project', 'Default project for migrated data', 'system')
ON CONFLICT DO NOTHING;

-- Migrate existing data to default project
UPDATE model_performance_metrics SET project_id = 'default' WHERE project_id IS NULL;
UPDATE fine_tuning_dataset SET project_id = 'default' WHERE project_id IS NULL;
UPDATE llm_response_cache SET project_id = 'default' WHERE project_id IS NULL;
