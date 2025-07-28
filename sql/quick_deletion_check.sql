-- ⚡ QUICK CHANNEL DELETION VERIFICATION
-- Replace '@metalsole' with the actual handle you want to check
-- Copy-paste this entire query into Supabase SQL editor

WITH target_channel AS (
  SELECT channel_id, channel_name, handle
  FROM youtube_channels 
  WHERE handle = '@metalsole'  -- 🔧 CHANGE THIS to your channel handle
)
SELECT 
  '🏢 Channel Record' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM target_channel

UNION ALL

SELECT 
  '📹 Videos' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM youtube_videos yv
CROSS JOIN target_channel tc 
WHERE yv.channel_id = tc.channel_id

UNION ALL

SELECT 
  '📝 Transcripts' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM transcripts t
CROSS JOIN target_channel tc
WHERE t.video_id IN (
  SELECT yv.video_id 
  FROM youtube_videos yv 
  WHERE yv.channel_id = tc.channel_id
)

UNION ALL

SELECT 
  '📋 Summaries' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM summaries s
CROSS JOIN target_channel tc
WHERE s.video_id IN (
  SELECT yv.video_id 
  FROM youtube_videos yv 
  WHERE yv.channel_id = tc.channel_id
)

UNION ALL

SELECT 
  '📚 Chapters' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM video_chapters vc
CROSS JOIN target_channel tc
WHERE vc.video_id IN (
  SELECT yv.video_id 
  FROM youtube_videos yv 
  WHERE yv.channel_id = tc.channel_id
)

UNION ALL

SELECT 
  '🧠 Memory Snippets' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM memory_snippets ms
CROSS JOIN target_channel tc
WHERE ms.video_id IN (
  SELECT yv.video_id 
  FROM youtube_videos yv 
  WHERE yv.channel_id = tc.channel_id
)

UNION ALL

SELECT 
  '💬 Chat Conversations' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM chat_conversations cc
CROSS JOIN target_channel tc
WHERE cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id

UNION ALL

SELECT 
  '💭 Chat Messages' as data_type,
  COUNT(*) as remaining_count,
  CASE 
    WHEN COUNT(*) = 0 THEN '✅ COMPLETELY DELETED' 
    ELSE '❌ STILL EXISTS - DELETION FAILED!' 
  END as status
FROM chat_messages cm
WHERE cm.conversation_id IN (
  SELECT cc.id 
  FROM chat_conversations cc
  CROSS JOIN target_channel tc
  WHERE cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id
)

ORDER BY data_type;

-- 📊 SUMMARY: 
-- If deletion was successful, ALL counts should be 0 and ALL status should be "✅ COMPLETELY DELETED"
-- If you see any "❌ STILL EXISTS" then the deletion has issues that need investigation