-- Add Chapter prompt to ai_prompts table using the current chapter summarization prompt
INSERT INTO ai_prompts (name, prompt_text, is_default, description) VALUES (
    'Chapter',
    'Please provide a comprehensive summary of this specific chapter from a YouTube video.

Chapter Title: {chapter_title}

Focus on:
- The main topics and concepts covered in this chapter
- Key insights and takeaways specific to this section
- Actionable strategies or advice mentioned
- Important examples, statistics, or case studies
- Any warnings or pitfalls discussed

Structure your response as follows:

## Chapter Overview
Brief summary of what this chapter covers.

## Key Points
Main concepts and insights from this chapter.

## Actionable Takeaways  
Practical advice or strategies that can be implemented.

## Important Details
Specific examples, statistics, or details worth noting.

## Warnings & Considerations
Any cautions or potential pitfalls mentioned.

Please analyze this chapter transcript:

{chapter_transcript}',
    false,
    'Comprehensive prompt for creating focused chapter summaries'
);