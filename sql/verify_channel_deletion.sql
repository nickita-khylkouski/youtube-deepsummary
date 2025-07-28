-- 🔍 Channel Deletion Verification Queries
-- Run these SQL queries in Supabase after deleting a channel to verify complete deletion
-- Just replace '@your_handle' with the actual handle you deleted (e.g., '@metalsole')

-- ==================================================
-- ⚡ SUPER QUICK ONE-LINER (Copy-Paste Ready)
-- ==================================================
-- Replace '@your_handle' with actual handle like '@metalsole' and run:

/*
WITH ch AS (SELECT channel_id FROM youtube_channels WHERE handle = '@your_handle')
SELECT 'Channel' as type, COUNT(*) as count FROM ch
UNION ALL SELECT 'Videos', COUNT(*) FROM youtube_videos WHERE channel_id IN (SELECT channel_id FROM ch)
UNION ALL SELECT 'Chats', COUNT(*) FROM chat_conversations WHERE channel_id IN (SELECT channel_id FROM ch) OR original_channel_id IN (SELECT channel_id FROM ch);
*/

-- ==================================================
-- 🎯 AUTOMATIC VERIFICATION BY HANDLE
-- ==================================================
-- Replace '@your_handle' with the actual handle like '@metalsole'
-- The queries will automatically find the channel ID

-- 1️⃣ Quick verification (should all return 0 after deletion)
WITH target_channel AS (
  SELECT channel_id, channel_name, handle
  FROM youtube_channels 
  WHERE handle = '@your_handle'  -- 🔧 CHANGE THIS: Replace with actual handle like '@metalsole'
)
SELECT 
  'Channel Record' as table_name, 
  COUNT(*) as remaining_count,
  CASE WHEN COUNT(*) = 0 THEN '✅ DELETED' ELSE '❌ STILL EXISTS' END as status
FROM target_channel

UNION ALL

SELECT 
  'Videos' as table_name,
  COUNT(*) as remaining_count,
  CASE WHEN COUNT(*) = 0 THEN '✅ DELETED' ELSE '❌ STILL EXISTS' END as status
FROM youtube_videos yv
JOIN target_channel tc ON yv.channel_id = tc.channel_id

UNION ALL

SELECT 
  'Chat Conversations' as table_name,
  COUNT(*) as remaining_count,
  CASE WHEN COUNT(*) = 0 THEN '✅ DELETED' ELSE '❌ STILL EXISTS' END as status
FROM chat_conversations cc
JOIN target_channel tc ON (cc.channel_id = tc.channel_id OR cc.original_channel_id = tc.channel_id);

-- ==================================================
-- 📋 COMPREHENSIVE VERIFICATION BY HANDLE
-- ==================================================
-- Replace '@your_handle' with the actual handle like '@metalsole'

-- Get channel ID from handle for comprehensive check
WITH channel_info AS (
  SELECT channel_id, channel_name, handle
  FROM youtube_channels 
  WHERE handle = '@your_handle'  -- 🔧 CHANGE THIS: Replace with actual handle like '@metalsole'
),
video_list AS (
  SELECT v.video_id
  FROM youtube_videos v
  JOIN channel_info c ON v.channel_id = c.channel_id
)

-- Count all associated data (should all be 0 after deletion)
SELECT 
  '🏢 Channel Records' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM channel_info

UNION ALL

SELECT 
  '📹 Videos' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM video_list

UNION ALL

SELECT 
  '📝 Transcripts' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM transcripts t
WHERE t.video_id IN (SELECT video_id FROM video_list)

UNION ALL

SELECT 
  '📋 Summaries' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM summaries s
WHERE s.video_id IN (SELECT video_id FROM video_list)

UNION ALL

SELECT 
  '📚 Chapters' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM video_chapters vc
WHERE vc.video_id IN (SELECT video_id FROM video_list)

UNION ALL

SELECT 
  '🧠 Memory Snippets' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM memory_snippets ms
WHERE ms.video_id IN (SELECT video_id FROM video_list)

UNION ALL

SELECT 
  '💬 Chat Conversations' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM chat_conversations cc
JOIN channel_info c ON (cc.channel_id = c.channel_id OR cc.original_channel_id = c.channel_id)

UNION ALL

SELECT 
  '💭 Chat Messages' as check_type,
  COUNT(*) as count,
  CASE WHEN COUNT(*) = 0 THEN '✅ CLEAN' ELSE '❌ ORPHANED DATA FOUND!' END as status
FROM chat_messages cm
WHERE cm.conversation_id IN (
  SELECT cc.id 
  FROM chat_conversations cc
  JOIN channel_info c ON (cc.channel_id = c.channel_id OR cc.original_channel_id = c.channel_id)
);

-- ==================================================
-- 🔍 DETAILED ORPHANED DATA INVESTIGATION
-- ==================================================

-- Find any orphaned chat conversations (no matching channel)
SELECT 
  'Orphaned Chat Conversations' as issue_type,
  cc.id as conversation_id,
  cc.channel_id,
  cc.original_channel_id,
  cc.title,
  cc.created_at
FROM chat_conversations cc
LEFT JOIN youtube_channels yc1 ON cc.channel_id = yc1.channel_id
LEFT JOIN youtube_channels yc2 ON cc.original_channel_id = yc2.channel_id
WHERE (cc.channel_id IS NOT NULL AND yc1.channel_id IS NULL)
   OR (cc.original_channel_id IS NOT NULL AND yc2.channel_id IS NULL)
   OR (cc.channel_id IS NULL AND cc.original_channel_id IS NULL);

-- Find any orphaned chat messages (no matching conversation)
SELECT 
  'Orphaned Chat Messages' as issue_type,
  cm.id as message_id,
  cm.conversation_id,
  cm.role,
  LEFT(cm.content, 50) || '...' as content_preview,
  cm.created_at
FROM chat_messages cm
LEFT JOIN chat_conversations cc ON cm.conversation_id = cc.id
WHERE cc.id IS NULL;

-- Find any orphaned memory snippets (no matching video)
SELECT 
  'Orphaned Memory Snippets' as issue_type,
  ms.id as snippet_id,
  ms.video_id,
  LEFT(ms.snippet_text, 50) || '...' as snippet_preview,
  ms.created_at
FROM memory_snippets ms
LEFT JOIN youtube_videos yv ON ms.video_id = yv.video_id
WHERE yv.video_id IS NULL;

-- Find any orphaned transcripts (no matching video)
SELECT 
  'Orphaned Transcripts' as issue_type,
  t.id as transcript_id,
  t.video_id,
  t.language_used,
  t.created_at
FROM transcripts t
LEFT JOIN youtube_videos yv ON t.video_id = yv.video_id
WHERE yv.video_id IS NULL;

-- Find any orphaned summaries (no matching video)
SELECT 
  'Orphaned Summaries' as issue_type,
  s.id as summary_id,
  s.video_id,
  s.model_used,
  LEFT(s.summary_text, 50) || '...' as summary_preview,
  s.created_at
FROM summaries s
LEFT JOIN youtube_videos yv ON s.video_id = yv.video_id
WHERE yv.video_id IS NULL;

-- Find any orphaned chapters (no matching video)
SELECT 
  'Orphaned Chapters' as issue_type,
  vc.id as chapter_id,
  vc.video_id,
  vc.created_at
FROM video_chapters vc
LEFT JOIN youtube_videos yv ON vc.video_id = yv.video_id
WHERE yv.video_id IS NULL;

-- ==================================================
-- 🧹 CLEANUP QUERIES (USE WITH CAUTION!)
-- ==================================================
-- Only run these if you find orphaned data and want to clean it up

/*
-- Clean up orphaned chat messages
DELETE FROM chat_messages 
WHERE conversation_id NOT IN (SELECT id FROM chat_conversations);

-- Clean up orphaned chat conversations (no matching channel)
DELETE FROM chat_conversations 
WHERE (channel_id IS NOT NULL AND channel_id NOT IN (SELECT channel_id FROM youtube_channels))
   OR (original_channel_id IS NOT NULL AND original_channel_id NOT IN (SELECT channel_id FROM youtube_channels))
   OR (channel_id IS NULL AND original_channel_id IS NULL);

-- Clean up orphaned memory snippets
DELETE FROM memory_snippets 
WHERE video_id NOT IN (SELECT video_id FROM youtube_videos);

-- Clean up orphaned transcripts
DELETE FROM transcripts 
WHERE video_id NOT IN (SELECT video_id FROM youtube_videos);

-- Clean up orphaned summaries
DELETE FROM summaries 
WHERE video_id NOT IN (SELECT video_id FROM youtube_videos);

-- Clean up orphaned chapters
DELETE FROM video_chapters 
WHERE video_id NOT IN (SELECT video_id FROM youtube_videos);
*/