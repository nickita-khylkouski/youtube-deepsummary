-- Migration script to remove uploader column and index
-- Run this in Supabase SQL Editor after verifying all functionality works

-- Step 1: Drop the uploader index
DROP INDEX IF EXISTS idx_youtube_videos_uploader;

-- Step 2: Drop the uploader column
ALTER TABLE youtube_videos DROP COLUMN IF EXISTS uploader;

-- Verification queries:
-- Check that column is removed:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'youtube_videos' AND column_name = 'uploader';
-- Should return 0 rows

-- Check that data is still accessible:
-- SELECT COUNT(*) FROM youtube_videos;
-- SELECT COUNT(*) FROM youtube_channels;