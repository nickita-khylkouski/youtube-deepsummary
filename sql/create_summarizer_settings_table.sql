-- Create table for summarizer settings
CREATE TABLE IF NOT EXISTS summarizer_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default summarizer settings
INSERT INTO summarizer_settings (setting_key, setting_value, setting_type, description) VALUES
('preferred_provider', 'openai', 'string', 'Preferred AI provider for summarization: openai or anthropic'),
('model', 'gpt-4.1', 'string', 'AI model to use for summarization (provider-specific)'),
('temperature', '0.7', 'float', 'Temperature setting for AI responses (0.0 to 2.0)'),
('max_tokens', '8192', 'integer', 'Maximum number of tokens in AI responses'),
('enable_chapter_awareness', 'true', 'boolean', 'Use chapter information to improve summary structure'),
('enable_metadata_inclusion', 'true', 'boolean', 'Include video metadata in summaries'),
('enable_clickable_chapters', 'true', 'boolean', 'Add clickable YouTube chapter links to summaries'),
('fallback_provider', 'anthropic', 'string', 'Fallback provider if primary provider fails'),
('retry_on_failure', 'true', 'boolean', 'Retry summarization with fallback provider on failure'),
('max_retry_attempts', '2', 'integer', 'Maximum number of retry attempts for failed summarization'),
('summary_format', 'structured', 'string', 'Summary format: structured, simple, or detailed'),
('enable_prompt_customization', 'true', 'boolean', 'Allow custom prompts to override default prompts'),
('auto_detect_language', 'true', 'boolean', 'Automatically detect and adapt to transcript language');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_summarizer_settings_key ON summarizer_settings(setting_key);

-- Create trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_summarizer_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_summarizer_settings_updated_at
    BEFORE UPDATE ON summarizer_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_summarizer_settings_updated_at();