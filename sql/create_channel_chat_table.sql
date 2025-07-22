-- Create channel_chat table for "Chat with a channel" feature
-- This table stores chat conversations with AI based on channel context

CREATE TABLE channel_chat (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel_id VARCHAR(24) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant')),
    content TEXT NOT NULL,
    model_used VARCHAR(50) DEFAULT 'gpt-4.1',
    context_summary TEXT, -- Summary of channel context used for this response
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraint to youtube_channels
    CONSTRAINT fk_channel_chat_channel_id 
        FOREIGN KEY (channel_id) 
        REFERENCES youtube_channels(channel_id) 
        ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_channel_chat_channel_id ON channel_chat(channel_id);
CREATE INDEX idx_channel_chat_session_id ON channel_chat(session_id);
CREATE INDEX idx_channel_chat_created_at ON channel_chat(created_at);
CREATE INDEX idx_channel_chat_channel_session ON channel_chat(channel_id, session_id);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_channel_chat_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_channel_chat_updated_at
    BEFORE UPDATE ON channel_chat
    FOR EACH ROW
    EXECUTE FUNCTION update_channel_chat_updated_at();

-- Add comments for documentation
COMMENT ON TABLE channel_chat IS 'Stores chat conversations with AI based on channel context';
COMMENT ON COLUMN channel_chat.channel_id IS 'YouTube channel ID this chat is about';
COMMENT ON COLUMN channel_chat.session_id IS 'Unique session identifier for grouping messages';
COMMENT ON COLUMN channel_chat.message_type IS 'Type of message: user or assistant';
COMMENT ON COLUMN channel_chat.content IS 'The actual message content';
COMMENT ON COLUMN channel_chat.model_used IS 'AI model used for assistant responses';
COMMENT ON COLUMN channel_chat.context_summary IS 'Summary of channel context used for this response';