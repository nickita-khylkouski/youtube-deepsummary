-- 🔍 COMPLETE CHANNEL DATA AUDIT
-- Shows ALL data associated with a channel by handle
-- Replace '@metalsole' with the actual channel handle you want to audit
-- Use this BEFORE deletion to see what will be deleted
-- Use this AFTER deletion to verify everything was removed (should all be empty)

-- ==================================================
-- 🏢 CHANNEL INFORMATION
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle, channel_url, description, 
         subscriber_count, video_count, thumbnail_url, created_at, updated_at
  FROM youtube_channels 
  WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS to your channel handle
)
SELECT 
  '🏢 CHANNEL INFO' as section,
  channel_id,
  channel_name,
  handle,
  channel_url,
  COALESCE(subscriber_count::text, 'Unknown') as subscribers,
  COALESCE(video_count::text, 'Unknown') as total_videos,
  created_at::text as created_date
FROM target_channel;

-- ==================================================
-- 📹 ALL VIDEOS FOR THIS CHANNEL
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '📹 VIDEOS' as section,
  yv.video_id,
  yv.title,
  yv.duration::text as duration_seconds,
  yv.published_at::text as published_date,
  yv.url_path,
  yv.created_at::text as imported_date
FROM youtube_videos yv
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY yv.published_at DESC;

-- ==================================================
-- 📝 ALL TRANSCRIPTS (FULL TEXT)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '📝 TRANSCRIPT FULL TEXT' as section,
  t.video_id,
  yv.title as video_title,
  t.language_used,
  LENGTH(t.formatted_transcript) as transcript_length,
  t.formatted_transcript as full_transcript_text,
  t.created_at::text as created_date
FROM transcripts t
JOIN youtube_videos yv ON t.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY t.created_at DESC;

-- ==================================================
-- 📋 ALL AI SUMMARIES (FULL TEXT)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '📋 AI SUMMARY FULL TEXT' as section,
  s.video_id,
  yv.title as video_title,
  s.model_used,
  LENGTH(s.summary_text) as summary_length,
  s.summary_text as full_summary_text,
  s.is_current::text as is_current_version,
  COALESCE(s.prompt_name, 'Default') as prompt_used,
  s.created_at::text as created_date
FROM summaries s
JOIN youtube_videos yv ON s.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY s.created_at DESC;

-- ==================================================
-- 📚 ALL VIDEO CHAPTERS (FULL DATA)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '📚 VIDEO CHAPTERS FULL DATA' as section,
  vc.video_id,
  yv.title as video_title,
  jsonb_array_length(vc.chapters_data) as chapter_count,
  vc.chapters_data as full_chapters_data,
  vc.created_at::text as created_date
FROM video_chapters vc
JOIN youtube_videos yv ON vc.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY vc.created_at DESC;

-- ==================================================
-- 📑 ALL CHAPTER SUMMARIES (FULL TEXT)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '📑 CHAPTER SUMMARIES FULL TEXT' as section,
  cs.video_id,
  yv.title as video_title,
  cs.chapter_title,
  cs.chapter_time::text as chapter_start_time,
  cs.model_used,
  LENGTH(cs.summary_text) as summary_length,
  cs.summary_text as full_chapter_summary_text,
  cs.is_current::text as is_current_version,
  cs.created_at::text as created_date
FROM chapter_summaries cs
JOIN youtube_videos yv ON cs.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY cs.created_at DESC;

-- ==================================================
-- 🧠 ALL MEMORY SNIPPETS (FULL TEXT)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '🧠 MEMORY SNIPPETS FULL TEXT' as section,
  ms.id as snippet_id,
  ms.video_id,
  yv.title as video_title,
  ms.snippet_text as full_snippet_text,
  ms.context_before as context_before,
  ms.context_after as context_after,
  array_to_string(ms.tags, ', ') as tags,
  LENGTH(ms.snippet_text) as snippet_length,
  ms.created_at::text as created_date
FROM memory_snippets ms
JOIN youtube_videos yv ON ms.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY ms.created_at DESC;

-- ==================================================
-- 💬 ALL CHAT CONVERSATIONS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '💬 CHAT CONVERSATIONS' as section,
  cc.id as conversation_id,
  cc.title as conversation_title,
  cc.chat_type,
  CASE 
    WHEN cc.channel_id = tc.channel_id THEN 'Channel-specific'
    WHEN cc.original_channel_id = tc.channel_id THEN 'Global (originated here)'
    ELSE 'Other'
  END as conversation_type,
  cc.model_used,
  cc.created_at::text as created_date,
  cc.updated_at::text as last_updated
FROM chat_conversations cc
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
ORDER BY cc.updated_at DESC;

-- ==================================================
-- 💭 ALL CHAT MESSAGES (FULL TEXT)
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '💭 CHAT MESSAGES FULL TEXT' as section,
  cm.id as message_id,
  cm.conversation_id,
  cc.title as conversation_title,
  cm.role as message_role,
  cm.content as full_message_content,
  LENGTH(cm.content) as message_length,
  cm.created_at::text as created_date
FROM chat_messages cm
JOIN chat_conversations cc ON cm.conversation_id = cc.id
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
ORDER BY cm.created_at DESC;

-- ==================================================
-- 📊 DATA SUMMARY COUNTS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
),
counts AS (
  SELECT 
    tc.channel_name,
    tc.handle,
    COUNT(DISTINCT yv.video_id) as total_videos,
    COUNT(DISTINCT t.id) as total_transcripts,
    COUNT(DISTINCT s.id) as total_summaries,
    COUNT(DISTINCT vc.id) as total_video_chapters,
    COUNT(DISTINCT ms.id) as total_memory_snippets,
    COUNT(DISTINCT cc.id) as total_chat_conversations,
    COUNT(DISTINCT cm.id) as total_chat_messages
  FROM target_channel tc
  LEFT JOIN youtube_videos yv ON yv.channel_id = tc.channel_id
  LEFT JOIN transcripts t ON t.video_id = yv.video_id
  LEFT JOIN summaries s ON s.video_id = yv.video_id
  LEFT JOIN video_chapters vc ON vc.video_id = yv.video_id
  LEFT JOIN memory_snippets ms ON ms.video_id = yv.video_id
  LEFT JOIN chat_conversations cc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
  LEFT JOIN chat_messages cm ON cm.conversation_id = cc.id
  GROUP BY tc.channel_name, tc.handle
)
SELECT 
  '📊 SUMMARY COUNTS' as section,
  channel_name || ' (' || handle || ')' as channel_info,
  total_videos::text as videos,
  total_transcripts::text as transcripts,
  total_summaries::text as ai_summaries,
  total_video_chapters::text as video_chapters,
  total_memory_snippets::text as memory_snippets,
  total_chat_conversations::text as chat_conversations,
  total_chat_messages::text as chat_messages
FROM counts;

-- ==================================================
-- 🎯 DELETION VERIFICATION
-- ==================================================
-- If you run this AFTER deletion, this section should show all zeros
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '🎯 DELETION CHECK' as section,
  CASE 
    WHEN EXISTS (SELECT 1 FROM target_channel) THEN '❌ CHANNEL STILL EXISTS'
    ELSE '✅ CHANNEL DELETED'
  END as channel_status,
  CASE 
    WHEN EXISTS (
      SELECT 1 FROM youtube_videos yv 
      JOIN target_channel tc ON yv.channel_id = tc.channel_id
    ) THEN '❌ VIDEOS STILL EXIST'
    ELSE '✅ VIDEOS DELETED'
  END as videos_status,
  CASE 
    WHEN EXISTS (
      SELECT 1 FROM chat_conversations cc
      JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
    ) THEN '❌ CHATS STILL EXIST'
    ELSE '✅ CHATS DELETED'
  END as chats_status;

-- 📝 USAGE INSTRUCTIONS:
-- 1. Replace '@metalsole' with your actual channel handle in ALL sections above
-- 2. Run this query BEFORE deletion to see all data that will be deleted
-- 3. Run this query AFTER deletion to verify everything was removed
-- 4. The last section (DELETION CHECK) will show if deletion was successful