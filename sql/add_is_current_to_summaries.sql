-- Add is_current column to summaries table for blog functionality
-- This column helps identify which summary is the current/active one for each video

-- Add the is_current column
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT FALSE;

-- Set all existing summaries to be current (since there's only one per video for now)
UPDATE summaries SET is_current = TRUE WHERE is_current IS NULL OR is_current = FALSE;

-- Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_summaries_is_current ON summaries(is_current);

-- Add a constraint to ensure only one current summary per video (optional)
-- This is commented out for now, but can be enabled if needed:
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_summaries_current_per_video 
-- ON summaries(video_id) WHERE is_current = TRUE;