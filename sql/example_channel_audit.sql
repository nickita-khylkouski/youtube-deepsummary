-- 📋 EXAMPLE: Complete Channel Data Audit for @metalsole
-- This shows what a comprehensive channel audit looks like
-- Copy this query and replace '@metalsole' with your actual handle

-- ==================================================
-- 🏢 CHANNEL INFORMATION
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle, channel_url, description, 
         subscriber_count, video_count, thumbnail_url, created_at, updated_at
  FROM youtube_channels 
  WHERE handle = '@metalsole'  -- 🔧 Replace with your handle
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
-- 📊 COMPLETE DATA SUMMARY
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
),
detailed_counts AS (
  SELECT 
    tc.channel_name,
    tc.handle,
    COUNT(DISTINCT yv.video_id) as videos,
    COUNT(DISTINCT t.id) as transcripts,
    COUNT(DISTINCT s.id) as summaries,
    COUNT(DISTINCT vc.id) as video_chapters,
    COUNT(DISTINCT ms.id) as memory_snippets,
    COUNT(DISTINCT cc.id) as chat_conversations,
    COUNT(DISTINCT cm.id) as chat_messages,
    -- Additional counts
    COUNT(DISTINCT CASE WHEN s.is_current = true THEN s.id END) as current_summaries,
    COUNT(DISTINCT s.model_used) as unique_ai_models,
    SUM(LENGTH(s.summary_text)) as total_summary_chars,
    SUM(LENGTH(t.formatted_transcript)) as total_transcript_chars,
    COUNT(DISTINCT ms.tags) as unique_snippet_tags
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
  '📊 DATA TOTALS' as section,
  channel_name || ' (' || handle || ')' as item,
  videos::text || ' videos' as count1,
  transcripts::text || ' transcripts' as count2,
  summaries::text || ' summaries (' || current_summaries::text || ' current)' as count3,
  memory_snippets::text || ' snippets' as count4,
  chat_conversations::text || ' conversations' as count5,
  chat_messages::text || ' chat messages' as count6
FROM detailed_counts

UNION ALL

SELECT 
  '📈 DATA SIZES' as section,
  'Content Volume' as item,
  CASE WHEN total_summary_chars > 0 THEN (total_summary_chars/1000)::text || 'K chars summaries' ELSE '0 summary chars' END as count1,
  CASE WHEN total_transcript_chars > 0 THEN (total_transcript_chars/1000)::text || 'K chars transcripts' ELSE '0 transcript chars' END as count2,
  unique_ai_models::text || ' AI models used' as count3,
  '' as count4,
  '' as count5,
  '' as count6
FROM detailed_counts;

-- ==================================================
-- 📹 ALL VIDEOS WITH STATUS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
)
SELECT 
  '📹 ALL VIDEOS' as section,
  yv.video_id,
  LEFT(yv.title, 60) || CASE WHEN LENGTH(yv.title) > 60 THEN '...' ELSE '' END as title,
  yv.published_at::date::text as published,
  -- Status indicators
  CASE WHEN EXISTS(SELECT 1 FROM transcripts t WHERE t.video_id = yv.video_id) THEN '📝✅' ELSE '📝❌' END ||
  CASE WHEN EXISTS(SELECT 1 FROM summaries s WHERE s.video_id = yv.video_id) THEN ' 📋✅' ELSE ' 📋❌' END ||
  CASE WHEN EXISTS(SELECT 1 FROM video_chapters vc WHERE vc.video_id = yv.video_id) THEN ' 📚✅' ELSE ' 📚❌' END ||
  ' 🧠' || COALESCE((SELECT COUNT(*)::text FROM memory_snippets ms WHERE ms.video_id = yv.video_id), '0') as status
FROM youtube_videos yv
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY yv.published_at DESC;

-- ==================================================
-- 📋 ALL AI SUMMARIES
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
)
SELECT 
  '📋 AI SUMMARIES' as section,
  s.video_id,
  LEFT(yv.title, 40) || '...' as video_title,
  s.model_used,
  CASE WHEN s.is_current THEN '✅ Current' ELSE '⏳ Old Version' END as status,
  s.version_number::text as version,
  LEFT(s.summary_text, 80) || '...' as preview
FROM summaries s
JOIN youtube_videos yv ON s.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY s.created_at DESC;

-- ==================================================
-- 🧠 ALL MEMORY SNIPPETS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
)
SELECT 
  '🧠 MEMORY SNIPPETS' as section,
  ms.id::text as snippet_id,
  LEFT(yv.title, 30) || '...' as from_video,
  array_to_string(ms.tags, ', ') as tags,
  LENGTH(ms.snippet_text)::text || ' chars' as size,
  LEFT(ms.snippet_text, 100) || '...' as preview
FROM memory_snippets ms
JOIN youtube_videos yv ON ms.video_id = yv.video_id
JOIN target_channel tc ON yv.channel_id = tc.channel_id
ORDER BY ms.created_at DESC;

-- ==================================================
-- 💬 ALL CHAT CONVERSATIONS & MESSAGES
-- ==================================================
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
)
SELECT 
  '💬 CHAT CONVERSATIONS' as section,
  cc.id::text as conversation_id,
  LEFT(cc.title, 50) || '...' as title,
  cc.chat_type,
  cc.model_used,
  (SELECT COUNT(*)::text FROM chat_messages cm WHERE cm.conversation_id = cc.id) || ' messages' as message_count,
  cc.created_at::date::text as created
FROM chat_conversations cc
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
ORDER BY cc.updated_at DESC;

-- Recent chat messages preview
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
)
SELECT 
  '💭 RECENT MESSAGES' as section,
  cm.conversation_id::text,
  LEFT(cc.title, 30) || '...' as conversation,
  cm.role,
  LENGTH(cm.content)::text || ' chars' as size,
  LEFT(cm.content, 80) || '...' as preview,
  cm.created_at::date::text as date
FROM chat_messages cm
JOIN chat_conversations cc ON cm.conversation_id = cc.id
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
ORDER BY cm.created_at DESC
LIMIT 10;

-- ==================================================
-- 🎯 FINAL VERIFICATION STATUS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 Replace
),
final_check AS (
  SELECT 
    EXISTS(SELECT 1 FROM target_channel) as channel_exists,
    (SELECT COUNT(*) FROM youtube_videos yv JOIN target_channel tc ON yv.channel_id = tc.channel_id) as video_count,
    (SELECT COUNT(*) FROM transcripts t JOIN youtube_videos yv ON t.video_id = yv.video_id JOIN target_channel tc ON yv.channel_id = tc.channel_id) as transcript_count,
    (SELECT COUNT(*) FROM summaries s JOIN youtube_videos yv ON s.video_id = yv.video_id JOIN target_channel tc ON yv.channel_id = tc.channel_id) as summary_count,
    (SELECT COUNT(*) FROM memory_snippets ms JOIN youtube_videos yv ON ms.video_id = yv.video_id JOIN target_channel tc ON yv.channel_id = tc.channel_id) as snippet_count,
    (SELECT COUNT(*) FROM chat_conversations cc JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)) as chat_count
)
SELECT 
  '🎯 STATUS CHECK' as section,
  CASE 
    WHEN NOT channel_exists THEN '✅ CHANNEL DELETED - All clear!'
    ELSE '⚠️ CHANNEL EXISTS with ' || 
         video_count::text || ' videos, ' ||
         summary_count::text || ' summaries, ' ||
         snippet_count::text || ' snippets, ' ||
         chat_count::text || ' chats'
  END as status,
  channel_exists::text as exists,
  (video_count + transcript_count + summary_count + snippet_count + chat_count)::text as total_records
FROM final_check;

-- 📝 LEGEND:
-- 📝 = Transcripts, 📋 = Summaries, 📚 = Chapters, 🧠 = Memory Snippets
-- ✅ = Present/Current, ❌ = Missing, ⏳ = Old Version
-- Use this query to see EVERYTHING before deletion, then run again after to verify all data is gone!