-- MIGRATION SCRIPT: Run these commands in order in Supabase SQL Editor
-- ================================================================

-- STEP 1: Create youtube_channels table
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

-- STEP 2: Add new columns to youtube_videos
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS channel_id VARCHAR(24);
ALTER TABLE youtube_videos ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- STEP 3: Migrate existing uploader data to youtube_channels
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
SELECT 
    'UC' || substr(md5(COALESCE(uploader, 'unknown')), 1, 22) as channel_id,
    COALESCE(uploader, 'Unknown Channel') as channel_name,
    MIN(created_at) as created_at,
    NOW() as updated_at
FROM youtube_videos 
WHERE uploader IS NOT NULL AND uploader != ''
GROUP BY uploader
ON CONFLICT (channel_id) DO NOTHING;

-- STEP 4: Link videos to channels
UPDATE youtube_videos 
SET channel_id = (
    SELECT c.channel_id 
    FROM youtube_channels c 
    WHERE c.channel_name = youtube_videos.uploader
)
WHERE uploader IS NOT NULL AND uploader != '' AND channel_id IS NULL;

-- STEP 5: Handle unknown channels
INSERT INTO youtube_channels (channel_id, channel_name, created_at, updated_at)
VALUES ('UC_unknown_channel_default', 'Unknown Channel', NOW(), NOW())
ON CONFLICT (channel_id) DO NOTHING;

UPDATE youtube_videos 
SET 
    channel_id = 'UC_unknown_channel_default',
    uploader = 'Unknown Channel'
WHERE (uploader IS NULL OR uploader = '') AND channel_id IS NULL;

-- STEP 6: Update video counts in channels
UPDATE youtube_channels 
SET video_count = (
    SELECT COUNT(*) 
    FROM youtube_videos v 
    WHERE v.channel_id = youtube_channels.channel_id
);

-- STEP 7: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_id ON youtube_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_name ON youtube_channels(channel_name);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_id ON youtube_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_uploader ON youtube_videos(uploader);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_published_at ON youtube_videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_created_at ON youtube_channels(created_at DESC);

-- STEP 8: Enable Row Level Security
ALTER TABLE youtube_channels ENABLE ROW LEVEL SECURITY;

-- STEP 9: Create policies for public access
CREATE POLICY "Allow public access to youtube_channels" ON youtube_channels FOR ALL USING (true);

-- VERIFICATION QUERIES (optional - run to check migration success)
-- =================================================================
-- SELECT 'Channels created:', COUNT(*) FROM youtube_channels;
-- SELECT 'Videos with channel_id:', COUNT(*) FROM youtube_videos WHERE channel_id IS NOT NULL;
-- SELECT 'Videos without channel_id:', COUNT(*) FROM youtube_videos WHERE channel_id IS NULL;
-- SELECT channel_name, video_count FROM youtube_channels ORDER BY video_count DESC LIMIT 10;