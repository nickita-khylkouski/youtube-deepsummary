-- Add handle column to youtube_channels table
-- YouTube handles are unique identifiers starting with @ (e.g., @channelname)

ALTER TABLE youtube_channels 
ADD COLUMN IF NOT EXISTS handle VARCHAR(100) UNIQUE;

-- Create index for handle column for better performance
CREATE INDEX IF NOT EXISTS idx_youtube_channels_handle ON youtube_channels(handle);

-- Add comment for documentation
COMMENT ON COLUMN youtube_channels.handle IS 'YouTube channel handle (e.g., @channelname)';