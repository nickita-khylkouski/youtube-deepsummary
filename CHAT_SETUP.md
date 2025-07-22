# Chat with Channel - Setup Guide

## Database Setup Required

The "Chat with a channel" feature requires a new database table that doesn't exist yet. Follow these steps to set it up:

### 1. Run the SQL Script

Execute the SQL script in your Supabase database:

```bash
# The SQL script is located at:
sql/create_channel_chat_table.sql
```

### 2. How to Apply the SQL Script

1. **Open Supabase Dashboard**
   - Go to your Supabase project dashboard
   - Navigate to the "SQL Editor" tab

2. **Run the SQL Script**
   - Copy the entire contents of `sql/create_channel_chat_table.sql`
   - Paste it into the SQL Editor
   - Click "Run" to execute the script

3. **Verify Table Creation**
   - Go to the "Table Editor" tab
   - You should see a new table called `channel_chat`

### 3. Table Structure

The `channel_chat` table includes:
- `id` (UUID, primary key)
- `channel_id` (VARCHAR, foreign key to youtube_channels)
- `session_id` (VARCHAR, groups messages into conversations)
- `message_type` (VARCHAR, 'user' or 'assistant')
- `content` (TEXT, the actual message)
- `model_used` (VARCHAR, AI model used for responses)
- `context_summary` (TEXT, summary of context used)
- `created_at` and `updated_at` timestamps

### 4. Features After Setup

Once the table is created, you can:
- 💬 Chat with any channel that has AI summaries
- 🤖 Use different AI models (OpenAI GPT-4.1, Anthropic Claude)
- 📝 Access all video summaries as context
- 💾 Maintain conversation history across sessions
- 🔄 Create multiple chat sessions per channel

### 5. Navigation

The chat feature is accessible from:
- Channel overview page (chat card)
- Channel sub-pages (chat navigation button)
- Direct URL: `/@{channel_handle}/chat`

### 6. Error Messages

If you see "Failed to save user message", it means the database table hasn't been created yet. Follow steps 1-2 above to resolve this.

### 7. Troubleshooting

If you encounter issues:
1. Check that the SQL script ran without errors
2. Verify the table exists in the Table Editor
3. Ensure your Supabase permissions allow table creation
4. Check the browser console for detailed error messages

## Ready to Chat! 🚀

After completing the setup, you can start having intelligent conversations with your YouTube channels based on their AI summaries!