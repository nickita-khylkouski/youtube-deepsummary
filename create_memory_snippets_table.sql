-- SQL commands to create the memory_snippets table in Supabase
-- Copy and paste these commands into your Supabase SQL Editor

CREATE TABLE memory_snippets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id VARCHAR(11) NOT NULL,
    snippet_text TEXT NOT NULL,
    context_before TEXT,
    context_after TEXT,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_memory_snippets_video_id ON memory_snippets(video_id);
CREATE INDEX idx_memory_snippets_created_at ON memory_snippets(created_at DESC);
CREATE INDEX idx_memory_snippets_tags ON memory_snippets USING GIN(tags);

-- Enable Row Level Security
ALTER TABLE memory_snippets ENABLE ROW LEVEL SECURITY;

-- Create policy to allow public access (adjust based on your security needs)
CREATE POLICY "Allow public access to memory_snippets" ON memory_snippets FOR ALL USING (true);