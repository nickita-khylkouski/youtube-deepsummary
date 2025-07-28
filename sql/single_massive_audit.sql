-- 🔥 SINGLE MASSIVE CHANNEL AUDIT - EVERYTHING IN ONE RESULT
-- Replace '@metalsole' with your actual channel handle
-- This shows ALL data in one giant table - transcripts, summaries, everything!

WITH target_channel AS (
  SELECT channel_id, channel_name, handle FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)

-- 🏢 CHANNEL INFO
SELECT 
  '01_🏢 CHANNEL INFO' as data_type,
  tc.channel_name as item_title,
  tc.handle as identifier,
  'Basic Info' as content_type,
  'Channel: ' || tc.channel_name || ' (' || tc.handle || ')' as full_content,
  tc.channel_id as extra_info
FROM target_channel tc

UNION ALL

-- 📹 ALL VIDEOS
SELECT 
  '02_📹 VIDEOS' as data_type,
  yv.title as item_title,
  yv.video_id as identifier,
  'Video Info' as content_type,
  'Title: ' || yv.title || E'\n' ||
  'Video ID: ' || yv.video_id || E'\n' ||
  'Published: ' || COALESCE(yv.published_at::text, 'Unknown') || E'\n' ||
  'Duration: ' || COALESCE(yv.duration::text, 'Unknown') || ' seconds' as full_content,
  yv.url_path as extra_info
FROM youtube_videos yv
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 📝 FULL TRANSCRIPTS
SELECT 
  '03_📝 TRANSCRIPTS' as data_type,
  yv.title as item_title,
  t.video_id as identifier,
  'Full Transcript (' || t.language_used || ')' as content_type,
  t.formatted_transcript as full_content,
  'Length: ' || LENGTH(t.formatted_transcript)::text || ' chars' as extra_info
FROM transcripts t
JOIN youtube_videos yv ON t.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 📋 FULL AI SUMMARIES  
SELECT 
  '04_📋 AI SUMMARIES' as data_type,
  yv.title as item_title,
  s.video_id as identifier,
  'AI Summary (' || s.model_used || ')' as content_type,
  s.summary_text as full_content,
  'Length: ' || LENGTH(s.summary_text)::text || ' chars | Current: ' || s.is_current::text as extra_info
FROM summaries s
JOIN youtube_videos yv ON s.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 📚 FULL CHAPTERS DATA
SELECT 
  '05_📚 CHAPTERS' as data_type,
  yv.title as item_title,
  vc.video_id as identifier,
  'Video Chapters' as content_type,
  vc.chapters_data::text as full_content,
  'Count: ' || jsonb_array_length(vc.chapters_data)::text || ' chapters' as extra_info
FROM video_chapters vc
JOIN youtube_videos yv ON vc.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 📑 FULL CHAPTER SUMMARIES
SELECT 
  '06_📑 CHAPTER SUMMARIES' as data_type,
  yv.title || ' - ' || cs.chapter_title as item_title,
  cs.video_id as identifier,
  'Chapter Summary (' || cs.model_used || ')' as content_type,
  cs.summary_text as full_content,
  'Chapter: ' || cs.chapter_title || ' | Time: ' || cs.chapter_time::text || 's | Current: ' || cs.is_current::text as extra_info
FROM chapter_summaries cs
JOIN youtube_videos yv ON cs.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 🧠 FULL MEMORY SNIPPETS
SELECT 
  '07_🧠 MEMORY SNIPPETS' as data_type,
  yv.title as item_title,
  ms.id::text as identifier,
  'Memory Snippet' as content_type,
  'SNIPPET TEXT:' || E'\n' || ms.snippet_text || E'\n\n' ||
  'CONTEXT BEFORE:' || E'\n' || COALESCE(ms.context_before, 'None') || E'\n\n' ||
  'CONTEXT AFTER:' || E'\n' || COALESCE(ms.context_after, 'None') as full_content,
  'Tags: ' || array_to_string(ms.tags, ', ') || ' | Length: ' || LENGTH(ms.snippet_text)::text as extra_info
FROM memory_snippets ms
JOIN youtube_videos yv ON ms.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

-- 💬 CHAT CONVERSATIONS
SELECT 
  '08_💬 CONVERSATIONS' as data_type,
  cc.title as item_title,
  cc.id::text as identifier,
  'Chat Conversation (' || cc.chat_type || ')' as content_type,
  'Title: ' || cc.title || E'\n' ||
  'Type: ' || cc.chat_type || E'\n' ||
  'Model: ' || cc.model_used || E'\n' ||
  'Created: ' || cc.created_at::text || E'\n' ||
  'Updated: ' || cc.updated_at::text as full_content,
  CASE 
    WHEN cc.channel_id = tc.channel_id THEN 'Channel-specific'
    WHEN cc.original_channel_id = tc.channel_id THEN 'Global (originated here)'
    ELSE 'Other'
  END as extra_info
FROM chat_conversations cc
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)

UNION ALL

-- 💭 FULL CHAT MESSAGES
SELECT 
  '09_💭 CHAT MESSAGES' as data_type,
  cc.title || ' - ' || cm.role as item_title,
  cm.id::text as identifier,
  'Chat Message (' || cm.role || ')' as content_type,
  cm.content as full_content,
  'Conversation: ' || cc.title || ' | Length: ' || LENGTH(cm.content)::text || ' chars' as extra_info
FROM chat_messages cm
JOIN chat_conversations cc ON cm.conversation_id = cc.id
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)

UNION ALL

-- 📊 DATA COUNTS SUMMARY
SELECT 
  '00_📊 SUMMARY' as data_type,
  'Data Totals for ' || tc.channel_name as item_title,
  tc.channel_id as identifier,
  'Complete Summary' as content_type,
  'CHANNEL: ' || tc.channel_name || ' (' || tc.handle || ')' || E'\n\n' ||
  '📹 VIDEOS: ' || COUNT(DISTINCT yv.video_id)::text || E'\n' ||
  '📝 TRANSCRIPTS: ' || COUNT(DISTINCT t.id)::text || E'\n' || 
  '📋 AI SUMMARIES: ' || COUNT(DISTINCT s.id)::text || E'\n' ||
  '📚 VIDEO CHAPTERS: ' || COUNT(DISTINCT vc.id)::text || E'\n' ||
  '📑 CHAPTER SUMMARIES: ' || COUNT(DISTINCT cs.id)::text || E'\n' ||
  '🧠 MEMORY SNIPPETS: ' || COUNT(DISTINCT ms.id)::text || E'\n' ||
  '💬 CHAT CONVERSATIONS: ' || COUNT(DISTINCT cc.id)::text || E'\n' ||
  '💭 CHAT MESSAGES: ' || COUNT(DISTINCT cm.id)::text || E'\n\n' ||
  '📏 CONTENT SIZES:' || E'\n' ||
  'Total Summary Text: ' || COALESCE(SUM(LENGTH(s.summary_text))::text, '0') || ' chars' || E'\n' ||
  'Total Transcript Text: ' || COALESCE(SUM(LENGTH(t.formatted_transcript))::text, '0') || ' chars' as full_content,
  'Complete audit for ' || tc.handle as extra_info
FROM target_channel tc
LEFT JOIN youtube_videos yv ON yv.channel_id = tc.channel_id
LEFT JOIN transcripts t ON t.video_id = yv.video_id
LEFT JOIN summaries s ON s.video_id = yv.video_id
LEFT JOIN video_chapters vc ON vc.video_id = yv.video_id
LEFT JOIN chapter_summaries cs ON cs.video_id = yv.video_id
LEFT JOIN memory_snippets ms ON ms.video_id = yv.video_id
LEFT JOIN chat_conversations cc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
LEFT JOIN chat_messages cm ON cm.conversation_id = cc.id
GROUP BY tc.channel_name, tc.handle, tc.channel_id

ORDER BY data_type, item_title;

-- 📝 INSTRUCTIONS:
-- 1. Replace '@metalsole' with your actual channel handle
-- 2. This will show EVERYTHING in one giant scrollable table
-- 3. Look at the 'full_content' column - that's where all the text is
-- 4. Use this before deletion to see what will be removed
-- 5. Use after deletion - should be empty except for summary showing all zeros