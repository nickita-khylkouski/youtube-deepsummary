-- Fix foreign key relationship between youtube_videos and youtube_channels
-- This addresses the PGRST200 error when trying to JOIN tables

-- First, let's check if the foreign key constraint exists
-- If it doesn't exist, we need to add it

-- Step 1: Add the foreign key constraint if it doesn't exist
-- Note: This will fail if there are orphaned records, so we handle that first

-- Step 2: Clean up any orphaned records (videos without valid channel_id)
-- Update any videos that have invalid channel_ids to NULL
UPDATE youtube_videos 
SET channel_id = NULL 
WHERE channel_id IS NOT NULL 
AND channel_id NOT IN (SELECT channel_id FROM youtube_channels);

-- Step 3: Add the foreign key constraint
-- Drop the constraint if it exists (in case it's malformed)
ALTER TABLE youtube_videos DROP CONSTRAINT IF EXISTS youtube_videos_channel_id_fkey;

-- Add the proper foreign key constraint
ALTER TABLE youtube_videos 
ADD CONSTRAINT youtube_videos_channel_id_fkey 
FOREIGN KEY (channel_id) 
REFERENCES youtube_channels(channel_id) 
ON DELETE SET NULL;

-- Step 4: Verify the constraint was added
-- This query will show the constraint details
SELECT conname, contype, conrelid::regclass, confrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'youtube_videos_channel_id_fkey';

-- Step 5: Update table statistics to help the query planner
ANALYZE youtube_videos;
ANALYZE youtube_channels;