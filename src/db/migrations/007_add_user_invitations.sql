-- Migration: Add user invitations table for team management
-- This migration adds support for user invitations and audit event types

-- Create user invitations table
CREATE TABLE IF NOT EXISTS user_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) DEFAULT '',
    last_name VARCHAR(100) DEFAULT '',
    role VARCHAR(50) NOT NULL CHECK (role IN ('super_admin', 'admin', 'user', 'viewer')),
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    message TEXT DEFAULT '',
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'cancelled', 'expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP,
    accepted_by UUID REFERENCES users(id)
);

-- Create indexes for user invitations
CREATE INDEX idx_user_invitations_email ON user_invitations(email);
CREATE INDEX idx_user_invitations_token ON user_invitations(invitation_token);
CREATE INDEX idx_user_invitations_status ON user_invitations(status);
CREATE INDEX idx_user_invitations_expires ON user_invitations(expires_at);
CREATE INDEX idx_user_invitations_invited_by ON user_invitations(invited_by);

-- Update audit_logs table to use proper event_type enum instead of generic action
-- First, let's see what columns exist
DO $$
BEGIN
    -- Add event_type column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'audit_logs' AND column_name = 'event_type') THEN
        ALTER TABLE audit_logs ADD COLUMN event_type VARCHAR(100);
        
        -- Copy action values to event_type
        UPDATE audit_logs SET event_type = action WHERE event_type IS NULL;
        
        -- Make event_type NOT NULL
        ALTER TABLE audit_logs ALTER COLUMN event_type SET NOT NULL;
    END IF;
    
    -- Add severity column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'audit_logs' AND column_name = 'severity') THEN
        ALTER TABLE audit_logs ADD COLUMN severity VARCHAR(20) DEFAULT 'medium' 
            CHECK (severity IN ('low', 'medium', 'high', 'critical'));
    END IF;
END$$;

-- Create indexes for new audit log columns
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_logs(severity);

-- Add some sample audit events for user invitations (these would be added by the application)
INSERT INTO audit_logs (
    user_id, event_type, severity, resource_type, details, success, created_at
) VALUES 
    (
        (SELECT id FROM users WHERE email = 'admin@kairos.dev' LIMIT 1),
        'user_invited',
        'medium',
        'user_invitation',
        '{"invited_email": "demo@example.com", "role": "user"}',
        true,
        CURRENT_TIMESTAMP
    )
ON CONFLICT DO NOTHING;

-- Function to clean up expired invitations
CREATE OR REPLACE FUNCTION cleanup_expired_invitations() RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE user_invitations 
    SET status = 'expired' 
    WHERE status = 'pending' 
    AND expires_at < CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- Function to accept invitation and create user
CREATE OR REPLACE FUNCTION accept_invitation(
    invitation_token_param VARCHAR,
    password_hash_param VARCHAR,
    username_param VARCHAR DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    invitation_record RECORD;
    new_user_id UUID;
    generated_username VARCHAR;
BEGIN
    -- Get invitation
    SELECT * INTO invitation_record 
    FROM user_invitations 
    WHERE invitation_token = invitation_token_param 
    AND status = 'pending' 
    AND expires_at > CURRENT_TIMESTAMP;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invalid or expired invitation token';
    END IF;
    
    -- Generate username if not provided
    IF username_param IS NULL THEN
        generated_username := split_part(invitation_record.email, '@', 1);
        
        -- Ensure username is unique
        WHILE EXISTS (SELECT 1 FROM users WHERE username = generated_username) LOOP
            generated_username := generated_username || '_' || floor(random() * 1000)::text;
        END LOOP;
    ELSE
        generated_username := username_param;
    END IF;
    
    -- Create user
    INSERT INTO users (
        email, username, password_hash, first_name, last_name, role, status
    ) VALUES (
        invitation_record.email,
        generated_username,
        password_hash_param,
        invitation_record.first_name,
        invitation_record.last_name,
        invitation_record.role,
        'active'
    ) RETURNING id INTO new_user_id;
    
    -- Update invitation status
    UPDATE user_invitations 
    SET status = 'accepted', 
        accepted_at = CURRENT_TIMESTAMP,
        accepted_by = new_user_id
    WHERE id = invitation_record.id;
    
    -- Create default project for user
    INSERT INTO projects (name, description, owner_id)
    VALUES (
        'Default Project - ' || generated_username,
        'Default project for ' || invitation_record.first_name || ' ' || invitation_record.last_name,
        new_user_id
    );
    
    -- Add user as project owner
    INSERT INTO project_members (project_id, user_id, role)
    VALUES (
        (SELECT id FROM projects WHERE owner_id = new_user_id ORDER BY created_at DESC LIMIT 1),
        new_user_id,
        'owner'
    );
    
    RETURN new_user_id;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON user_invitations TO PUBLIC;
GRANT USAGE ON SEQUENCE user_invitations_id_seq TO PUBLIC;

COMMIT;
