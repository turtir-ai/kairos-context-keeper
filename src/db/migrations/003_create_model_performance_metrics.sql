-- Migration: Create model performance metrics table for Sprint 5
-- Purpose: Store historical LLM model performance data for intelligent routing

CREATE TABLE IF NOT EXISTS model_performance_metrics (
    id SERIAL PRIMARY KEY,
    model_key VARCHAR(255) NOT NULL,  -- Format: provider_model (e.g., ollama_llama3.1:8b)
    task_type VARCHAR(100) NOT NULL,   -- coding, reasoning, creative, general
    project_id VARCHAR(255),           -- For multi-project support (future)
    
    -- Performance metrics
    response_time_ms FLOAT NOT NULL,
    tokens_generated INTEGER,
    tokens_per_second FLOAT,
    
    -- Quality metrics
    success BOOLEAN DEFAULT TRUE,
    guardian_approved BOOLEAN,         -- If passed GuardianAgent validation
    user_feedback_score INTEGER,       -- 1-5 rating if provided
    error_message TEXT,
    
    -- Cost tracking
    estimated_cost DECIMAL(10, 6) DEFAULT 0.0,
    actual_tokens_used INTEGER,
    
    -- Context
    prompt_length INTEGER,
    context_length INTEGER,
    temperature FLOAT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    task_id VARCHAR(255),
    session_id VARCHAR(255)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_model_performance_model_key ON model_performance_metrics(model_key);
CREATE INDEX IF NOT EXISTS idx_model_performance_task_type ON model_performance_metrics(task_type);
CREATE INDEX IF NOT EXISTS idx_model_performance_created_at ON model_performance_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_model_performance_project_id ON model_performance_metrics(project_id);

-- Composite index for model selection queries
CREATE INDEX IF NOT EXISTS idx_model_performance_selection ON model_performance_metrics(model_key, task_type, success, created_at);

-- Create aggregated view for quick access to model stats
CREATE OR REPLACE VIEW model_performance_summary AS
SELECT 
    model_key,
    task_type,
    COUNT(*) as total_requests,
    AVG(response_time_ms) as avg_response_time_ms,
    AVG(tokens_per_second) as avg_tokens_per_second,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate,
    SUM(CASE WHEN guardian_approved THEN 1 ELSE 0 END)::FLOAT / NULLIF(SUM(CASE WHEN guardian_approved IS NOT NULL THEN 1 ELSE 0 END), 0) as guardian_approval_rate,
    AVG(user_feedback_score) as avg_user_rating,
    SUM(estimated_cost) as total_cost,
    MAX(created_at) as last_used
FROM model_performance_metrics
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'  -- Only consider recent data
GROUP BY model_key, task_type;

-- Function to calculate model performance score
CREATE OR REPLACE FUNCTION calculate_model_score(
    p_model_key VARCHAR,
    p_task_type VARCHAR,
    p_weight_speed FLOAT DEFAULT 0.3,
    p_weight_success FLOAT DEFAULT 0.4,
    p_weight_cost FLOAT DEFAULT 0.1,
    p_weight_quality FLOAT DEFAULT 0.2
) RETURNS FLOAT AS $$
DECLARE
    v_score FLOAT := 0.0;
    v_stats RECORD;
BEGIN
    -- Get model stats
    SELECT 
        avg_response_time_ms,
        success_rate,
        COALESCE(guardian_approval_rate, success_rate) as quality_rate,
        total_cost / NULLIF(total_requests, 0) as avg_cost
    INTO v_stats
    FROM model_performance_summary
    WHERE model_key = p_model_key 
    AND task_type = p_task_type;
    
    IF NOT FOUND THEN
        RETURN 0.5; -- Default score for new models
    END IF;
    
    -- Calculate weighted score (normalize each metric to 0-1 range)
    v_score := 
        (p_weight_speed * (1.0 - LEAST(v_stats.avg_response_time_ms / 5000.0, 1.0))) +  -- Speed: faster is better
        (p_weight_success * COALESCE(v_stats.success_rate, 0.5)) +                      -- Success rate
        (p_weight_cost * (1.0 - LEAST(COALESCE(v_stats.avg_cost, 0) / 0.01, 1.0))) +  -- Cost: cheaper is better
        (p_weight_quality * COALESCE(v_stats.quality_rate, 0.5));                      -- Quality
    
    RETURN v_score;
END;
$$ LANGUAGE plpgsql;

-- Table for caching LLM responses
CREATE TABLE IF NOT EXISTS llm_response_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 hash of prompt + model + params
    model_key VARCHAR(255) NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    metadata JSONB,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_cache_key ON llm_response_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_response_cache(expires_at);

-- Cleanup function for expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache() RETURNS void AS $$
BEGIN
    DELETE FROM llm_response_cache 
    WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;
