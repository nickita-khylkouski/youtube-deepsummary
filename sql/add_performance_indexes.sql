-- Performance indexes for optimized channel queries
-- Run these in your Supabase SQL editor to dramatically improve query speed

-- Fast channel listing and video ordering
create index if not exists idx_youtube_videos_channel_created
  on youtube_videos (channel_id, created_at desc);

-- Fast nested lookups for transcripts
create index if not exists idx_transcripts_video_created
  on transcripts (video_id, created_at desc);

-- Fast nested lookups for summaries with is_current priority
create index if not exists idx_summaries_video_is_current_created
  on summaries (video_id, is_current, created_at desc);

-- Fast nested lookups for video chapters
create index if not exists idx_video_chapters_video_created
  on video_chapters (video_id, created_at desc);

-- Partial index for "current" summaries (highly selective)
create index if not exists idx_summaries_current
  on summaries (video_id, created_at desc)
  where is_current = true;

-- Index for user snippets by channel (for counts)
create index if not exists idx_user_snippets_video_created
  on user_snippets (video_id, created_at desc);

-- Composite index for transcript validation queries
create index if not exists idx_transcripts_validation
  on transcripts (video_id, char_length(formatted_transcript))
  where char_length(formatted_transcript) > 100;

-- Channel lookups by handle (if not already exists)
create index if not exists idx_youtube_channels_handle
  on youtube_channels (handle);

-- Channel lookups by ID (if not already exists) 
create index if not exists idx_youtube_channels_id
  on youtube_channels (channel_id);