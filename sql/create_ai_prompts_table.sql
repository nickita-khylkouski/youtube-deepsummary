-- Create AI Prompts table for managing custom AI summary prompts
CREATE TABLE ai_prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    prompt_text TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on name for faster lookups
CREATE INDEX idx_ai_prompts_name ON ai_prompts(name);

-- Create index on is_default for finding default prompt
CREATE INDEX idx_ai_prompts_default ON ai_prompts(is_default);

-- Insert default prompt
INSERT INTO ai_prompts (name, prompt_text, is_default, description) VALUES (
    'Default Summary',
    'You are an expert at creating comprehensive yet concise summaries of video transcripts. Please analyze the following transcript and create a well-structured summary.

Format your response with the following sections:

## Overview
Provide a brief overview of the video''s main theme and purpose in 2-3 sentences.

## Main Topics
• List the key topics discussed in bullet points
• Focus on the most important themes and concepts
• Keep each point concise but informative

## Key Takeaways & Insights
• Highlight the most valuable insights and conclusions
• Include any unique perspectives or novel approaches
• Focus on actionable or memorable information

## Actionable Strategies
• List specific strategies, methods, or techniques mentioned
• Include step-by-step processes if applicable
• Focus on practical implementation advice

## Specific Details & Examples
• Include important statistics, numbers, or data points
• Mention specific examples, case studies, or anecdotes
• Note any tools, resources, or references mentioned

## Warnings & Common Mistakes
• Highlight any warnings or cautionary advice given
• List common mistakes or pitfalls to avoid
• Include any "don''t do this" type of guidance

## Resources & Next Steps
• List any books, websites, tools, or resources mentioned
• Include suggested next steps or follow-up actions
• Note any related content or recommended viewing

Keep the summary comprehensive but focused on the most valuable information. Use bullet points for easy readability.',
    true,
    'Comprehensive default prompt for creating structured video summaries'
);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_ai_prompts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_prompts_updated_at_trigger
    BEFORE UPDATE ON ai_prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_prompts_updated_at();

-- Ensure only one default prompt at a time
CREATE OR REPLACE FUNCTION ensure_single_default_prompt()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = TRUE THEN
        UPDATE ai_prompts SET is_default = FALSE WHERE id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER ensure_single_default_prompt_trigger
    BEFORE INSERT OR UPDATE ON ai_prompts
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_default_prompt();