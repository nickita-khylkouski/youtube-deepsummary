-- Add title and description columns to youtube_channels table
-- These fields will store the official channel title and description from YouTube API

-- Add channel_title column (separate from channel_name for clarity)
-- channel_name is what we store locally, channel_title is the official YouTube title
ALTER TABLE youtube_channels 
ADD COLUMN IF NOT EXISTS channel_title TEXT;

-- Add channel_description column 
ALTER TABLE youtube_channels 
ADD COLUMN IF NOT EXISTS channel_description TEXT;

-- Create indexes for better search performance
CREATE INDEX IF NOT EXISTS idx_youtube_channels_title ON youtube_channels(channel_title);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_description ON youtube_channels USING GIN(to_tsvector('english', channel_description));

-- Add comments for documentation
COMMENT ON COLUMN youtube_channels.channel_title IS 'Official YouTube channel title from API';
COMMENT ON COLUMN youtube_channels.channel_description IS 'Official YouTube channel description from API';

-- Update the updated_at timestamp for tracking
UPDATE youtube_channels SET updated_at = NOW() WHERE channel_title IS NULL OR channel_description IS NULL;