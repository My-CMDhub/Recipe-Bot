-- =====================================================
-- TABLE: prompt_metrics
-- =====================================================
-- Purpose: Track prompt size and context limit errors
-- Think of it as: Monitoring system for AI prompt health
-- =====================================================
CREATE TABLE IF NOT EXISTS prompt_metrics (
    id BIGSERIAL PRIMARY KEY,
    
    -- Which prediction is this for? (optional, can be NULL for other prompts)
    prediction_id BIGINT REFERENCES predictions(id) ON DELETE SET NULL,
    
    -- User who triggered this prompt
    user_phone TEXT,
    
    -- Prompt size in characters
    prompt_size_chars INTEGER NOT NULL,
    
    -- Estimated token count (rough estimate: chars / 4)
    estimated_tokens INTEGER NOT NULL,
    
    -- Which LLM was used? 'gemini', 'mistral', 'deepseek', 'openai'
    llm_used TEXT,
    
    -- Did this hit context limit? True if error occurred
    context_limit_hit BOOLEAN DEFAULT FALSE,
    
    -- Error message if context limit was hit
    error_message TEXT,
    
    -- Error code from API (if available)
    error_code TEXT,
    
    -- Was the request successful despite size?
    request_successful BOOLEAN DEFAULT TRUE,
    
    -- When was this prompt sent?
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_prompt_metrics_prediction_id ON prompt_metrics(prediction_id);
CREATE INDEX IF NOT EXISTS idx_prompt_metrics_user_phone ON prompt_metrics(user_phone);
CREATE INDEX IF NOT EXISTS idx_prompt_metrics_created_at ON prompt_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_metrics_context_limit ON prompt_metrics(context_limit_hit);

-- =====================================================
-- VIEW: prompt_metrics_summary
-- =====================================================
-- Purpose: Quick summary view for monitoring in Supabase
-- =====================================================
CREATE OR REPLACE VIEW prompt_metrics_summary AS
SELECT 
    DATE(created_at) as date,
    llm_used,
    COUNT(*) as total_prompts,
    AVG(prompt_size_chars) as avg_chars,
    AVG(estimated_tokens) as avg_tokens,
    MAX(prompt_size_chars) as max_chars,
    MAX(estimated_tokens) as max_tokens,
    COUNT(*) FILTER (WHERE context_limit_hit = TRUE) as context_limit_errors,
    COUNT(*) FILTER (WHERE request_successful = TRUE) as successful_requests
FROM prompt_metrics
GROUP BY DATE(created_at), llm_used
ORDER BY date DESC, llm_used;

