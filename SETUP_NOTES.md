# Notes Setup Instructions

## Current Status

✅ **Working Now**: Notes functionality with file fallback
- Highlighting text works and saves to `user_notes.txt`
- Notes persist on your local machine
- No more 500 errors

## To Enable Full Database Persistence

To make your notes persist across all devices and sessions (including incognito), you need to create the `user_notes` table in your Supabase database:

### Step 1: Open Supabase SQL Editor

1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Click on "SQL Editor" in the left sidebar

### Step 2: Run This SQL

Copy and paste this SQL into the editor and click "Run":

```sql
-- Create user_notes table
CREATE TABLE IF NOT EXISTS user_notes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    notes_content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_user_notes_updated_at ON user_notes(updated_at DESC);

-- Enable Row Level Security
ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;

-- Create policy for public access
CREATE POLICY "Allow public access to user_notes" ON user_notes FOR ALL USING (true);
```

### Step 3: Test Database Connection

Run this to verify it's working:

```bash
python3 create_notes_table.py
```

You should see "✅ Notes functionality working!" instead of errors.

## How It Works

### Current File Fallback
- Notes saved to `user_notes.txt` in project directory
- Works immediately, no setup required
- Persists on local machine only

### After Database Setup
- Notes saved to Supabase database
- Persists across all devices and sessions
- Works in incognito mode
- Synchronized across all instances

## Usage

1. **Highlight Text**: On any transcript or summary page, highlight text
2. **Add to Notes**: Click the "📝 Add to Notes" button that appears
3. **View/Edit**: Go to the Notes page to see and edit all your saved highlights
4. **Auto-Save**: Notes are automatically saved every 30 seconds

Your highlighted text will be formatted like:
```
--- Transcript from "Video Title" (Date) ---
Your highlighted text here
```

## Troubleshooting

If you see errors:
1. Make sure you ran the SQL in Supabase
2. Check your `SUPABASE_URL` and `SUPABASE_KEY` environment variables
3. The file fallback will always work as a backup

The system is designed to gracefully fall back to file storage if database access fails.