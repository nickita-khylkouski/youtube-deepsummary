-- Chat Settings Table
-- Stores user preferences for chat functionality
CREATE TABLE IF NOT EXISTS chat_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO chat_settings (setting_key, setting_value, description) VALUES
('default_model', 'claude-sonnet-4-20250514', 'Default AI model for channel chat'),
('chat_prompt_template', 'You are a helpful AI assistant answering questions about a YouTube channel based on AI summaries of its videos.

Format your responses with proper markdown for readability:
- Use bullet points (-) for lists
- Use **bold text** for emphasis
- Use clear section headers when appropriate
- Structure information logically with line breaks
- Be conversational, helpful, and reference specific videos when relevant

You have access to AI summaries from the YouTube channel "{channel_name}".

Here are all the AI summaries from this channel''s videos:

{ai_summaries}

Based on these summaries, please answer the user''s question about this channel''s content. You have comprehensive knowledge of all topics, themes, and insights covered in this channel''s videos.

Always format your response with clear structure and markdown formatting.

User question: {user_message}', 'Prompt template for channel chat with variables: {channel_name}, {ai_summaries}, {user_message}')
ON CONFLICT (setting_key) DO NOTHING;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_chat_settings_updated_at 
    BEFORE UPDATE ON chat_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();