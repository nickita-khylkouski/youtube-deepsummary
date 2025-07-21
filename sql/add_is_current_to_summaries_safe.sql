-- Add is_current column to summaries table for blog functionality
-- Safe approach that avoids trigger conflicts

-- Step 1: Add the is_current column with default FALSE
ALTER TABLE summaries ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT FALSE;

-- Step 2: Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_summaries_is_current ON summaries(is_current);

-- Step 3: Update summaries in smaller batches to avoid trigger conflicts
-- First, identify which summaries should be current (latest for each video)
WITH latest_summaries AS (
    SELECT DISTINCT ON (video_id) 
        id,
        video_id,
        created_at
    FROM summaries 
    ORDER BY video_id, created_at DESC
)
UPDATE summaries 
SET is_current = TRUE 
WHERE id IN (SELECT id FROM latest_summaries)
AND is_current IS DISTINCT FROM TRUE;

-- Step 4: Verify the update worked
-- This query should show the count of current summaries
-- SELECT COUNT(*) as current_summaries FROM summaries WHERE is_current = TRUE;