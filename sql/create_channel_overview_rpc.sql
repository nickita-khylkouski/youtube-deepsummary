-- Optimized RPC function for channel overview data
-- This pushes all validation and filtering logic to Postgres for maximum performance

create or replace function channel_overview(cid text, vlimit int default 50)
returns table(
  video_id text,
  title text,
  channel_id text,
  channel_name text,
  duration text,
  published_at timestamptz,
  created_at timestamptz,
  url_path text,
  uploader text,
  has_transcript boolean,
  has_summary boolean,
  summary_text text,
  chapters jsonb,
  snippet_count bigint
) language sql as $$
  -- Use CTE to compute snippet count once instead of per-row
  with channel_snippet_count as (
    select count(*) as total_snippets
    from user_snippets ms
    join youtube_videos yv on ms.video_id = yv.video_id
    where yv.channel_id = cid
  )
  select
    v.video_id,
    v.title,
    v.channel_id,
    v.channel_name,
    v.duration,
    v.published_at,
    v.created_at,
    v.url_path,
    v.uploader,
    -- Server-side transcript validation
    exists (
      select 1 from transcripts t
      where t.video_id = v.video_id
        and char_length(coalesce(t.formatted_transcript, '')) > 100
        and not (t.formatted_transcript ilike any (array[
          '%transcript extraction failed%',
          '%no transcript available%',
          '%transcript not available%',
          '%failed to extract%',
          '%error extracting%'
        ]))
    ) as has_transcript,
    -- Check for current summary
    exists (
      select 1 from summaries s
      where s.video_id = v.video_id and s.is_current = true
    ) as has_summary,
    -- Get best summary (current first, then latest)
    (
      select s.summary_text from summaries s
      where s.video_id = v.video_id
      order by s.is_current desc, s.created_at desc
      limit 1
    ) as summary_text,
    -- Get latest chapters
    (
      select vc.chapters_data from video_chapters vc
      where vc.video_id = v.video_id
      order by vc.created_at desc
      limit 1
    ) as chapters,
    -- Get snippet count from CTE (computed once for entire channel)
    csc.total_snippets as snippet_count
  from youtube_videos v
  cross join channel_snippet_count csc
  where v.channel_id = cid
  order by v.created_at desc
  limit vlimit
$$;

-- Also create a lighter function for just stats
create or replace function channel_stats(cid text)
returns table(
  total_videos bigint,
  summary_count bigint,
  videos_with_transcripts bigint,
  videos_without_transcripts bigint,
  snippet_count bigint
) language sql as $$
  select
    count(*) as total_videos,
    count(*) filter (where exists (
      select 1 from summaries s 
      where s.video_id = v.video_id and s.is_current = true
    )) as summary_count,
    count(*) filter (where exists (
      select 1 from transcripts t
      where t.video_id = v.video_id
        and char_length(coalesce(t.formatted_transcript, '')) > 100
        and not (t.formatted_transcript ilike any (array[
          '%transcript extraction failed%',
          '%no transcript available%',
          '%transcript not available%',
          '%failed to extract%',
          '%error extracting%'
        ]))
    )) as videos_with_transcripts,
    count(*) - count(*) filter (where exists (
      select 1 from transcripts t
      where t.video_id = v.video_id
        and char_length(coalesce(t.formatted_transcript, '')) > 100
        and not (t.formatted_transcript ilike any (array[
          '%transcript extraction failed%',
          '%no transcript available%',
          '%transcript not available%',
          '%failed to extract%',
          '%error extracting%'
        ]))
    )) as videos_without_transcripts,
    (
      select count(*) from user_snippets ms
      join youtube_videos yv on ms.video_id = yv.video_id
      where yv.channel_id = cid
    ) as snippet_count
  from youtube_videos v
  where v.channel_id = cid
$$;