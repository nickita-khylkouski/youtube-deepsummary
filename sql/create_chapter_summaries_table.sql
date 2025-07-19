-- Create table for storing chapter summaries
CREATE TABLE IF NOT EXISTS chapter_summaries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    chapter_time INTEGER NOT NULL, -- Start time of the chapter in seconds
    chapter_title TEXT NOT NULL, -- Title of the chapter
    summary_text TEXT NOT NULL, -- AI-generated summary for this chapter
    model_used VARCHAR(50) DEFAULT 'claude-sonnet-4-20250514',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(video_id, chapter_time) -- Ensure one summary per chapter per video
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_video_id ON chapter_summaries(video_id);
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_video_chapter ON chapter_summaries(video_id, chapter_time);
CREATE INDEX IF NOT EXISTS idx_chapter_summaries_created_at ON chapter_summaries(created_at DESC);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE chapter_summaries ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public access (adjust based on your security needs)
CREATE POLICY "Allow public access to chapter_summaries" ON chapter_summaries FOR ALL USING (true);