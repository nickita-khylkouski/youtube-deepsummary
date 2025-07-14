-- Migration script to add youtube_channels table and update existing data
-- Run this AFTER creating the new tables with create_tables.sql

-- Step 1: Add the new column to youtube_videos if it doesn't exist
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS channel_id VARCHAR(24);
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- Step 2: Create youtube_channels table if it doesn't exist (redundant safety check)
CREATE TABLE IF NOT EXISTS youtube_channels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel_id VARCHAR(24) UNIQUE NOT NULL,
    channel_name TEXT NOT NULL,
    channel_url TEXT,
    description TEXT,
    subscriber_count INTEGER,
    video_count INTEGER,
    thumbnail_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 3: Migrate existing uploader data to youtube_channels
-- This creates channel records based on unique uploader names
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
SELECT 
    'UC' || substr(md5(COALESCE(uploader, 'unknown')), 1, 22) as channel_id, -- Generate fake channel_id from uploader name
    COALESCE(uploader, 'Unknown Channel') as channel_name,
    MIN(created_at) as created_at, -- Use earliest video creation date
    NOW() as updated_at
FROM youtube_videos 
WHERE uploader IS NOT NULL AND uploader != ''
GROUP BY uploader
ON CONFLICT (channel_id) DO NOTHING; -- Skip if channel_id already exists

-- Step 4: Update youtube_videos to link to the new channel records
UPDATE youtube_videos 
SET channel_id = (
    SELECT c.channel_id 
    FROM youtube_channels c 
    WHERE c.channel_name = youtube_videos.uploader
)
WHERE uploader IS NOT NULL AND uploader != '' AND channel_id IS NULL;

-- Step 5: Handle videos with null/empty uploader - create a default channel
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
VALUES ('UC_unknown_channel_default', 'Unknown Channel', NOW(), NOW())
ON CONFLICT (channel_id) DO NOTHING;

-- Update videos with null uploader to use the default channel
UPDATE youtube_videos 
SET 
    channel_id = 'UC_unknown_channel_default',
    uploader = 'Unknown Channel'
WHERE (uploader IS NULL OR uploader = '') AND channel_id IS NULL;

-- Step 6: Add the foreign key constraint (this will fail if there are orphaned records)
-- Comment this out if you want to add the constraint manually later
-- ALTER TABLE youtube_videos ADD CONSTRAINT fk_youtube_videos_channel_id 
--     FOREIGN KEY (channel_id) REFERENCES youtube_channels(channel_id) ON DELETE SET NULL;

-- Step 7: Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_id ON youtube_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_name ON youtube_channels(channel_name);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_id ON youtube_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_uploader ON youtube_videos(uploader);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_published_at ON youtube_videos(published_at DESC);

-- Step 8: Update video counts in channels table
UPDATE youtube_channels 
SET video_count = (
    SELECT COUNT(*) 
    FROM youtube_videos v 
    WHERE v.channel_id = youtube_channels.channel_id
);

-- Verification queries (uncomment to run):
-- SELECT 'Channels created:', COUNT(*) FROM youtube_channels;
-- SELECT 'Videos with channel_id:', COUNT(*) FROM youtube_videos WHERE channel_id IS NOT NULL;
-- SELECT 'Videos without channel_id:', COUNT(*) FROM youtube_videos WHERE channel_id IS NULL;
-- SELECT 'Channel stats:', channel_name, video_count FROM youtube_channels ORDER BY video_count DESC;