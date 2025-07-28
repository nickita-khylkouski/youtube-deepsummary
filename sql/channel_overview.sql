-- 📊 CHANNEL DATA OVERVIEW
-- Quick overview of all data associated with a channel
-- Replace '@metalsole' with the actual channel handle
-- Perfect for pre-deletion review and post-deletion verification

-- ==================================================
-- 🎯 CHANNEL OVERVIEW & DATA COUNTS
-- ==================================================
WITH target_channel AS (
  SELECT channel_id, channel_name, handle, created_at
  FROM youtube_channels 
  WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS to your channel handle
),
video_data AS (
  SELECT 
    yv.video_id,
    yv.title,
    yv.published_at,
    EXISTS(SELECT 1 FROM transcripts t WHERE t.video_id = yv.video_id) as has_transcript,
    EXISTS(SELECT 1 FROM summaries s WHERE s.video_id = yv.video_id) as has_summary,
    EXISTS(SELECT 1 FROM video_chapters vc WHERE vc.video_id = yv.video_id) as has_chapters,
    (SELECT COUNT(*) FROM memory_snippets ms WHERE ms.video_id = yv.video_id) as snippet_count
  FROM youtube_videos yv
  JOIN target_channel tc ON yv.channel_id = tc.channel_id
),
chat_data AS (
  SELECT 
    cc.id,
    cc.title,
    cc.chat_type,
    (SELECT COUNT(*) FROM chat_messages cm WHERE cm.conversation_id = cc.id) as message_count
  FROM chat_conversations cc
  JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id)
)

-- 1️⃣ Channel Information
SELECT 
  '🏢 CHANNEL INFO' as section,
  tc.channel_name as name,
  tc.handle,
  tc.created_at::date::text as created_date,
  '' as details
FROM target_channel tc

UNION ALL

-- 2️⃣ Data Summary Counts
SELECT 
  '📊 DATA SUMMARY' as section,
  'Total Records' as name,
  '' as handle,
  '' as created_date,
  (SELECT COUNT(*) FROM video_data)::text || ' videos, ' ||
  (SELECT COUNT(*) FROM video_data WHERE has_transcript)::text || ' transcripts, ' ||
  (SELECT COUNT(*) FROM video_data WHERE has_summary)::text || ' summaries, ' ||
  (SELECT COUNT(*) FROM video_data WHERE has_chapters)::text || ' with chapters, ' ||
  (SELECT SUM(snippet_count) FROM video_data)::text || ' snippets, ' ||
  (SELECT COUNT(*) FROM chat_data)::text || ' conversations, ' ||
  (SELECT SUM(message_count) FROM chat_data)::text || ' messages' as details

UNION ALL

-- 3️⃣ Recent Videos Preview
SELECT 
  '📹 RECENT VIDEOS' as section,
  LEFT(vd.title, 50) as name,
  vd.video_id as handle,
  vd.published_at::date::text as created_date,
  '📝' || CASE WHEN vd.has_transcript THEN '✅' ELSE '❌' END || 
  ' 📋' || CASE WHEN vd.has_summary THEN '✅' ELSE '❌' END ||
  ' 📚' || CASE WHEN vd.has_chapters THEN '✅' ELSE '❌' END ||
  ' 🧠' || vd.snippet_count::text as details
FROM video_data vd
ORDER BY vd.published_at DESC
LIMIT 10

UNION ALL

-- 4️⃣ Chat Conversations Preview
SELECT 
  '💬 CONVERSATIONS' as section,
  LEFT(cd.title, 50) as name,
  cd.id::text as handle,
  cd.chat_type as created_date,
  cd.message_count::text || ' messages' as details
FROM chat_data cd
ORDER BY cd.id
LIMIT 10;

-- ==================================================
-- 🔍 DETAILED BREAKDOWN BY DATA TYPE
-- ==================================================

-- Videos with missing data (potential issues)
WITH target_channel AS (
  SELECT channel_id FROM youtube_channels WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS
)
SELECT 
  '⚠️ VIDEOS MISSING DATA' as issue_type,
  yv.video_id,
  yv.title,
  CASE 
    WHEN NOT EXISTS(SELECT 1 FROM transcripts t WHERE t.video_id = yv.video_id) THEN 'No Transcript '
    ELSE ''
  END ||
  CASE 
    WHEN NOT EXISTS(SELECT 1 FROM summaries s WHERE s.video_id = yv.video_id) THEN 'No Summary '
    ELSE ''
  END ||
  CASE 
    WHEN NOT EXISTS(SELECT 1 FROM video_chapters vc WHERE vc.video_id = yv.video_id) THEN 'No Chapters'
    ELSE ''
  END as missing_data
FROM youtube_videos yv
JOIN target_channel tc ON yv.channel_id = tc.channel_id
WHERE NOT EXISTS(SELECT 1 FROM transcripts t WHERE t.video_id = yv.video_id)
   OR NOT EXISTS(SELECT 1 FROM summaries s WHERE s.video_id = yv.video_id)
   OR NOT EXISTS(SELECT 1 FROM video_chapters vc WHERE vc.video_id = yv.video_id);

-- ==================================================
-- 🧹 POST-DELETION VERIFICATION
-- ==================================================
-- Run this section after deletion - should show "Channel not found"
WITH verification AS (
  SELECT 
    EXISTS(SELECT 1 FROM youtube_channels WHERE handle = '@metalsole') as channel_exists,  -- 🔧 CHANGE THIS
    (SELECT COUNT(*) FROM youtube_videos yv 
     JOIN youtube_channels yc ON yv.channel_id = yc.channel_id 
     WHERE yc.handle = '@metalsole') as video_count,  -- 🔧 CHANGE THIS
    (SELECT COUNT(*) FROM chat_conversations cc
     JOIN youtube_channels yc ON (cc.channel_id = yc.channel_id OR cc.original_channel_id = yc.channel_id)
     WHERE yc.handle = '@metalsole') as chat_count  -- 🔧 CHANGE THIS
)
SELECT 
  '🎯 DELETION VERIFICATION' as check_type,
  CASE 
    WHEN channel_exists THEN '❌ DELETION FAILED - Channel still exists'
    WHEN video_count > 0 THEN '❌ DELETION FAILED - Videos still exist (' || video_count::text || ')'
    WHEN chat_count > 0 THEN '❌ DELETION FAILED - Chats still exist (' || chat_count::text || ')'
    ELSE '✅ DELETION SUCCESSFUL - All data removed'
  END as status,
  channel_exists::text as channel_exists,
  video_count::text as remaining_videos,
  chat_count::text as remaining_chats
FROM verification;

-- 📝 INSTRUCTIONS:
-- 1. Replace ALL instances of '@metalsole' with your actual channel handle
-- 2. Use this before deletion to see what data exists
-- 3. Use this after deletion to verify everything was removed
-- 4. The icons in RECENT VIDEOS show: 📝=transcript, 📋=summary, 📚=chapters, 🧠=snippet count