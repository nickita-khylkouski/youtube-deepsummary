-- FIXED MIGRATION SCRIPT
-- =======================

-- CHUNK 1: Create tables and columns (same as before)
CREATE TABLE IF NOT EXISTS youtube_channels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel_id VARCHAR(32) UNIQUE NOT NULL, -- Increased to 32 chars for safety
    channel_name TEXT NOT NULL,
    channel_url TEXT,
    description TEXT,
    subscriber_count INTEGER,
    video_count INTEGER,
    thumbnail_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add new columns to youtube_videos
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS channel_id VARCHAR(32); -- Increased to 32
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- CHUNK 2 (FIXED): Migrate existing uploader data - safer approach
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
SELECT 
    'UC' || substring(md5(COALESCE(uploader, 'unknown')), 1, 22) as channel_id,
    COALESCE(uploader, 'Unknown Channel') as channel_name,
    MIN(created_at) as created_at,
    NOW() as updated_at
FROM youtube_videos 
WHERE uploader IS NOT NULL AND uploader != ''
GROUP BY uploader
ON CONFLICT (channel_id) DO NOTHING;

-- CHUNK 3: Link videos to channels (same as before)
UPDATE youtube_videos 
SET channel_id = (
    SELECT c.channel_id 
    FROM youtube_channels c 
    WHERE c.channel_name = youtube_videos.uploader
)
WHERE uploader IS NOT NULL AND uploader != '' AND channel_id IS NULL;

-- CHUNK 4: Handle unknown channels (same as before)
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
VALUES ('UC_unknown_channel_default', 'Unknown Channel', NOW(), NOW())
ON CONFLICT (channel_id) DO NOTHING;

UPDATE youtube_videos 
SET 
    channel_id = 'UC_unknown_channel_default',
    uploader = 'Unknown Channel'
WHERE (uploader IS NULL OR uploader = '') AND channel_id IS NULL;

-- CHUNK 5: Update counts and indexes
UPDATE youtube_channels 
SET video_count = (
    SELECT COUNT(*) 
    FROM youtube_videos v 
    WHERE v.channel_id = youtube_channels.channel_id
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_id ON youtube_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_name ON youtube_channels(channel_name);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_id ON youtube_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_uploader ON youtube_videos(uploader);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_published_at ON youtube_videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_created_at ON youtube_channels(created_at DESC);

-- CHUNK 6: Security settings
ALTER TABLE youtube_channels ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to youtube_channels" ON youtube_channels FOR ALL USING (true);