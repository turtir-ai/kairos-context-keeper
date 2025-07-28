-- Migration: Create fine-tuning dataset table for Sprint 5
-- Purpose: Store failed tasks and corrections for autonomous model training

CREATE TABLE IF NOT EXISTS fine_tuning_dataset (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255),
    
    -- Input/Output pairs
    prompt TEXT NOT NULL,
    failed_output TEXT NOT NULL,
    correct_output TEXT,  -- User-provided or approved correction
    
    -- Error information
    failure_reason VARCHAR(255) NOT NULL,  -- guardian_rejected, user_rejected, error, timeout
    guardian_feedback TEXT,                -- GuardianAgent's specific feedback
    error_details TEXT,
    
    -- Metadata
    model_key VARCHAR(255) NOT NULL,       -- Which model produced the failure
    task_type VARCHAR(100),                -- coding, reasoning, creative, general
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',  -- pending, labeled, trained, rejected
    labeled_by VARCHAR(255),               -- User who provided correct output
    labeled_at TIMESTAMP,
    
    -- Training metadata
    training_batch_id VARCHAR(255),        -- Groups samples into training batches
    used_in_training BOOLEAN DEFAULT FALSE,
    training_score FLOAT,                  -- Performance score after training
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_fine_tuning_status ON fine_tuning_dataset(status);
CREATE INDEX IF NOT EXISTS idx_fine_tuning_task_id ON fine_tuning_dataset(task_id);
CREATE INDEX IF NOT EXISTS idx_fine_tuning_project_id ON fine_tuning_dataset(project_id);
CREATE INDEX IF NOT EXISTS idx_fine_tuning_model_key ON fine_tuning_dataset(model_key);
CREATE INDEX IF NOT EXISTS idx_fine_tuning_created_at ON fine_tuning_dataset(created_at);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_fine_tuning_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_fine_tuning_updated_at ON fine_tuning_dataset;
CREATE TRIGGER trigger_update_fine_tuning_updated_at
    BEFORE UPDATE ON fine_tuning_dataset
    FOR EACH ROW
    EXECUTE FUNCTION update_fine_tuning_updated_at();

-- View for training-ready samples
CREATE OR REPLACE VIEW fine_tuning_ready AS
SELECT 
    id,
    task_id,
    project_id,
    prompt,
    correct_output,
    model_key,
    task_type,
    failure_reason,
    guardian_feedback
FROM fine_tuning_dataset
WHERE status = 'labeled' 
    AND correct_output IS NOT NULL 
    AND NOT used_in_training
ORDER BY created_at;

-- Function to mark samples as used in training
CREATE OR REPLACE FUNCTION mark_samples_trained(
    p_batch_id VARCHAR,
    p_sample_ids INTEGER[]
) RETURNS INTEGER AS $$
DECLARE
    v_updated_count INTEGER;
BEGIN
    UPDATE fine_tuning_dataset
    SET 
        used_in_training = TRUE,
        training_batch_id = p_batch_id,
        status = 'trained'
    WHERE id = ANY(p_sample_ids);
    
    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RETURN v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- Statistics view for monitoring fine-tuning progress
CREATE OR REPLACE VIEW fine_tuning_stats AS
SELECT 
    model_key,
    task_type,
    failure_reason,
    COUNT(*) as total_samples,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_samples,
    SUM(CASE WHEN status = 'labeled' THEN 1 ELSE 0 END) as labeled_samples,
    SUM(CASE WHEN status = 'trained' THEN 1 ELSE 0 END) as trained_samples,
    AVG(CASE WHEN training_score IS NOT NULL THEN training_score ELSE NULL END) as avg_training_score
FROM fine_tuning_dataset
GROUP BY model_key, task_type, failure_reason;
