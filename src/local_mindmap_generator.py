"""
Local Mind Map Generator using AI

This module generates mind maps locally using AI models (OpenAI/Claude) 
and returns structured JSON data for vis.js visualization.
"""

import json
import logging
from typing import Dict, Any, Optional
from src.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalMindMapGenerator:
    """Generate mind maps locally using AI models"""
    
    def __init__(self):
        self.openai_available = Config.is_openai_configured()
        self.anthropic_available = Config.is_anthropic_configured()
        
        if not (self.openai_available or self.anthropic_available):
            raise ValueError("No AI model configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in environment.")
    
    def generate_mindmap_from_content(self, content: str, title: str = None) -> Dict[str, Any]:
        """
        Generate a mind map from content using AI
        
        Args:
            content (str): The content to generate mind map from (transcript/summary)
            title (str, optional): Title for the mind map
            
        Returns:
            Dict[str, Any]: Mind map data with central topic, main topics, and subtopics
        """
        try:
            # Create the prompt for mind map generation
            prompt = f"""
Analyze the following content and create a comprehensive mind map.

Content: {content[:3000]}...

Generate a mind map in JSON format with the following exact structure:
{{
    "central_topic": "Main central topic (concise title)",
    "main_topics": [
        {{
            "title": "Main topic 1",
            "subtopics": [
                {{
                    "title": "Subtopic 1.1",
                    "notes": "Brief note (max 15 words)"
                }},
                {{
                    "title": "Subtopic 1.2", 
                    "notes": "Brief note (max 15 words)"
                }}
            ]
        }},
        {{
            "title": "Main topic 2",
            "subtopics": [
                {{
                    "title": "Subtopic 2.1",
                    "notes": "Brief note (max 15 words)"
                }},
                {{
                    "title": "Subtopic 2.2",
                    "notes": "Brief note (max 15 words)"
                }}
            ]
        }},
        {{
            "title": "Main topic 3",
            "subtopics": [
                {{
                    "title": "Subtopic 3.1",
                    "notes": "Brief note (max 15 words)"
                }},
                {{
                    "title": "Subtopic 3.2",
                    "notes": "Brief note (max 15 words)"
                }}
            ]
        }}
    ]
}}

Requirements:
- Create exactly 3 main topics
- Each main topic should have 2-3 subtopics
- Keep notes brief (maximum 15 words each)
- Focus on the most important concepts
- Make titles clear and descriptive
- Return ONLY the JSON structure, no other text

JSON:
"""

            # Generate using available AI model
            if self.openai_available:
                result = self._generate_with_openai(prompt)
            elif self.anthropic_available:
                result = self._generate_with_anthropic(prompt)
            else:
                raise ValueError("No AI model available")
            
            # Parse and validate the result
            mindmap_data = self._parse_and_validate_json(result)
            logger.info(f"Successfully generated mind map with central topic: {mindmap_data['central_topic']}")
            return {
                "success": True,
                "data": mindmap_data,
                "model_used": "openai" if self.openai_available else "anthropic"
            }
            
        except Exception as e:
            logger.error(f"Error generating mind map: {str(e)}")
            fallback_data = self._get_fallback_mindmap(title or "Video Content")
            logger.info(f"Using fallback mind map data: {fallback_data}")
            return {
                "success": False,
                "error": str(e),
                "data": fallback_data
            }
    
    def _generate_with_openai(self, prompt: str) -> str:
        """Generate content using OpenAI API"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use gpt-4o-mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a mind map generator. Return only valid JSON, no explanations or markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate content using Anthropic Claude API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def _parse_and_validate_json(self, result: str) -> Dict[str, Any]:
        """Parse and validate the AI response JSON"""
        try:
            # Clean up the response
            result = result.strip()
            # Remove markdown code blocks if present
            if result.startswith('```json'):
                result = result.replace('```json', '').replace('```', '').strip()
            elif result.startswith('```'):
                result = result.replace('```', '').strip()
            
            if not result:
                raise ValueError("Empty response after cleanup")
            
            # Parse JSON
            try:
                mindmap_data = json.loads(result)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from AI: {str(e)}")
            
            # Validate structure
            required_keys = ['central_topic', 'main_topics']
            for key in required_keys:
                if key not in mindmap_data:
                    raise ValueError(f"Missing required key: {key}")
            
            # Validate main topics structure
            if not isinstance(mindmap_data['main_topics'], list):
                raise ValueError("main_topics must be a list")
            
            for i, topic in enumerate(mindmap_data['main_topics']):
                if not isinstance(topic, dict) or 'title' not in topic or 'subtopics' not in topic:
                    raise ValueError("Invalid main topic structure")
                
                for j, subtopic in enumerate(topic.get('subtopics', [])):
                    if not isinstance(subtopic, dict) or 'title' not in subtopic:
                        raise ValueError("Invalid subtopic structure")
            return mindmap_data
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise
    
    def _get_fallback_mindmap(self, title: str) -> Dict[str, Any]:
        """Generate a fallback mind map when AI generation fails"""
        return {
            "central_topic": title,
            "main_topics": [
                {
                    "title": "Key Concepts",
                    "subtopics": [
                        {"title": "Main Concept", "notes": "Primary idea discussed"},
                        {"title": "Supporting Ideas", "notes": "Additional concepts that support the main theme"}
                    ]
                },
                {
                    "title": "Important Details", 
                    "subtopics": [
                        {"title": "Specific Examples", "notes": "Concrete examples mentioned"},
                        {"title": "Technical Aspects", "notes": "Technical details or methodologies"}
                    ]
                },
                {
                    "title": "Practical Applications",
                    "subtopics": [
                        {"title": "Use Cases", "notes": "How this can be applied"},
                        {"title": "Benefits", "notes": "Advantages or positive outcomes"}
                    ]
                }
            ]
        }

# Create a singleton instance for easy importing
local_mindmap_generator = LocalMindMapGenerator()