-- Create table for video import settings
CREATE TABLE IF NOT EXISTS import_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(50) DEFAULT 'string',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default import settings
INSERT INTO import_settings (setting_key, setting_value, setting_type, description) VALUES
('default_max_results', '20', 'integer', 'Default number of videos to import per channel'),
('default_days_back', '30', 'integer', 'Default time range in days to look back for videos'),
('max_results_limit', '50', 'integer', 'Maximum number of videos that can be imported in one request'),
('enable_auto_summary', 'true', 'boolean', 'Automatically generate AI summaries for imported videos'),
('enable_transcript_extraction', 'true', 'boolean', 'Extract transcripts for imported videos'),
('enable_chapter_extraction', 'true', 'boolean', 'Extract video chapters for imported videos'),
('import_strategy', 'uploads_playlist', 'string', 'Primary strategy for finding videos: uploads_playlist, activities_api, or search_api'),
('fallback_strategies', 'activities_api,search_api', 'string', 'Comma-separated list of fallback strategies to try'),
('skip_existing_videos', 'true', 'boolean', 'Skip videos that already exist in the database'),
('batch_processing', 'true', 'boolean', 'Process videos in batches for better performance'),
('batch_size', '5', 'integer', 'Number of videos to process in each batch'),
('retry_failed_imports', 'true', 'boolean', 'Retry failed video imports'),
('max_retry_attempts', '3', 'integer', 'Maximum number of retry attempts for failed imports'),
('import_timeout', '300', 'integer', 'Timeout in seconds for import operations'),
('enable_progress_tracking', 'true', 'boolean', 'Show progress updates during import operations'),
('log_import_operations', 'true', 'boolean', 'Log detailed information about import operations');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_import_settings_key ON import_settings(setting_key); 