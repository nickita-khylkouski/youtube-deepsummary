-- Add summary history support to existing summaries table
-- This migration adds columns to track summary history and metadata

-- Add new columns to summaries table
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS summary_id SERIAL;
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS prompt_id INTEGER;
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS prompt_name VARCHAR(100);
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT TRUE;
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;

-- Add foreign key constraint to prompt_id (optional, since prompts might be deleted)
-- ALTER TABLE summaries ADD CONSTRAINT fk_summaries_prompt FOREIGN KEY (prompt_id) REFERENCES ai_prompts(id) ON DELETE SET NULL;

-- Create index on video_id and is_current for efficient queries
CREATE INDEX IF NOT EXISTS idx_summaries_video_current ON summaries(video_id, is_current);
CREATE INDEX IF NOT EXISTS idx_summaries_video_version ON summaries(video_id, version_number);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at);

-- Update existing summaries to set version numbers and current flags
-- This ensures existing data is properly versioned
UPDATE summaries 
SET 
    version_number = 1,
    is_current = TRUE,
    prompt_name = 'Default Summary'
WHERE version_number IS NULL;

-- Create function to manage summary versions
CREATE OR REPLACE FUNCTION manage_summary_versions()
RETURNS TRIGGER AS $$
BEGIN
    -- If this is a new summary for a video, set version number
    IF TG_OP = 'INSERT' THEN
        -- Get the highest version number for this video
        SELECT COALESCE(MAX(version_number), 0) + 1 
        INTO NEW.version_number
        FROM summaries 
        WHERE video_id = NEW.video_id;
        
        -- If this is set as current, mark all others as not current
        IF NEW.is_current = TRUE THEN
            UPDATE summaries 
            SET is_current = FALSE 
            WHERE video_id = NEW.video_id AND summary_id != NEW.summary_id;
        END IF;
    END IF;
    
    -- If this is an update and is_current is being set to true
    IF TG_OP = 'UPDATE' AND NEW.is_current = TRUE AND OLD.is_current = FALSE THEN
        UPDATE summaries 
        SET is_current = FALSE 
        WHERE video_id = NEW.video_id AND summary_id != NEW.summary_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically manage summary versions
DROP TRIGGER IF EXISTS manage_summary_versions_trigger ON summaries;
CREATE TRIGGER manage_summary_versions_trigger
    BEFORE INSERT OR UPDATE ON summaries
    FOR EACH ROW
    EXECUTE FUNCTION manage_summary_versions();

-- Add updated_at trigger for summaries if it doesn't exist
CREATE OR REPLACE FUNCTION update_summaries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_summaries_updated_at_trigger ON summaries;
CREATE TRIGGER update_summaries_updated_at_trigger
    BEFORE UPDATE ON summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_summaries_updated_at();