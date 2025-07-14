-- Create tables for YouTube Deep Summary application

-- Table for storing YouTube channel information
CREATE TABLE IF NOT EXISTS youtube_channels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel_id VARCHAR(32) UNIQUE NOT NULL, -- YouTube channel ID (UCxxxxx format)
    channel_name TEXT NOT NULL, -- Display name of the channel
    channel_url TEXT, -- Channel URL
    description TEXT, -- Channel description
    subscriber_count INTEGER, -- Number of subscribers
    video_count INTEGER, -- Total videos on channel
    thumbnail_url TEXT, -- Channel avatar/thumbnail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing YouTube video metadata
CREATE TABLE IF NOT EXISTS youtube_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) UNIQUE NOT NULL,
    channel_id VARCHAR(32) REFERENCES youtube_channels(channel_id) ON DELETE SET NULL,
    title TEXT,
    duration INTEGER,
    thumbnail_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE, -- When video was published on YouTube
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing video transcripts
CREATE TABLE IF NOT EXISTS transcripts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    transcript_data JSONB NOT NULL, -- Raw transcript with timestamps
    formatted_transcript TEXT NOT NULL, -- Formatted readable transcript
    language_used VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing video chapters
CREATE TABLE IF NOT EXISTS video_chapters (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    chapters_data JSONB, -- Array of chapter objects
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing AI summaries
CREATE TABLE IF NOT EXISTS summaries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    model_used VARCHAR(50) DEFAULT 'gpt-4.1',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for storing memory snippets from AI summaries
CREATE TABLE IF NOT EXISTS memory_snippets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    snippet_text TEXT NOT NULL,
    context_before TEXT, -- Text before the selected snippet for context
    context_after TEXT,  -- Text after the selected snippet for context
    tags TEXT[],         -- Array of tags for categorization
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_id ON youtube_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_channel_name ON youtube_channels(channel_name);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_video_id ON youtube_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel_id ON youtube_videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_video_id ON transcripts(video_id);
CREATE INDEX IF NOT EXISTS idx_video_chapters_video_id ON video_chapters(video_id);
CREATE INDEX IF NOT EXISTS idx_summaries_video_id ON summaries(video_id);
CREATE INDEX IF NOT EXISTS idx_memory_snippets_video_id ON memory_snippets(video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_created_at ON youtube_channels(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_created_at ON youtube_videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_published_at ON youtube_videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON summaries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_snippets_created_at ON memory_snippets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_snippets_tags ON memory_snippets USING GIN(tags);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE youtube_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE youtube_videos ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_chapters ENABLE ROW LEVEL SECURITY;
ALTER TABLE summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_snippets ENABLE ROW LEVEL SECURITY;

-- Create policies to allow public access (adjust based on your security needs)
CREATE POLICY "Allow public access to youtube_channels" ON youtube_channels FOR ALL USING (true);
CREATE POLICY "Allow public access to youtube_videos" ON youtube_videos FOR ALL USING (true);
CREATE POLICY "Allow public access to transcripts" ON transcripts FOR ALL USING (true);
CREATE POLICY "Allow public access to video_chapters" ON video_chapters FOR ALL USING (true);
CREATE POLICY "Allow public access to summaries" ON summaries FOR ALL USING (true);
CREATE POLICY "Allow public access to memory_snippets" ON memory_snippets FOR ALL USING (true);