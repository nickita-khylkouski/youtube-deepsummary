-- Add columns to support global chat history across all channels
-- This migration adds the necessary columns to the chat_conversations table

-- Step 1: Add original_channel_id column to track which channel conversation started from
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS original_channel_id VARCHAR(24);

-- Step 2: Copy existing channel_id to original_channel_id for backward compatibility
UPDATE chat_conversations 
SET original_channel_id = channel_id 
WHERE original_channel_id IS NULL;

-- Step 3: Add chat_type column to distinguish between channel-specific and global chats
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS chat_type VARCHAR(20) DEFAULT 'channel' CHECK (chat_type IN ('channel', 'global'));

-- Step 4: Update existing conversations to be 'channel' type
UPDATE chat_conversations 
SET chat_type = 'channel' 
WHERE chat_type IS NULL;

-- Step 5: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_conversations_original_channel_id ON chat_conversations(original_channel_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_chat_type ON chat_conversations(chat_type);

-- Step 6: Add comments to explain the new columns
COMMENT ON COLUMN chat_conversations.original_channel_id IS 'Channel where the conversation was originally started (required for all conversations)';
COMMENT ON COLUMN chat_conversations.chat_type IS 'Type of chat: channel-specific or global across all channels';

-- Note: The existing channel_id column can remain as is for backward compatibility
-- In the future, we could make it nullable if we want to support truly global conversations