"""
Cover Letter Generator Service
Uses OpenAI to generate personalized cover letters
"""

import os
from typing import Optional

# Initialize OpenAI client lazily
client = None

def get_openai_client():
    global client
    if client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
    return client


class CoverLetterGenerator:
    """Generate cover letters using AI"""
    
    @staticmethod
    def generate(
        resume_content: str,
        job_description: str,
        job_title: str,
        company_name: str,
        user_name: str = "",
        tone: str = "professional",
        additional_notes: str = ""
    ) -> dict:
        """
        Generate a cover letter based on resume and job description
        
        Args:
            resume_content: The text content of the resume
            job_description: The job posting description
            job_title: The title of the job
            company_name: Name of the company
            user_name: User's name for the letter
            tone: professional, enthusiastic, or conversational
            additional_notes: Any specific points to include
        
        Returns:
            dict with 'cover_letter' and 'key_points'
        """
        
        tone_instructions = {
            "professional": "Use a formal, professional tone suitable for corporate environments.",
            "enthusiastic": "Use an enthusiastic and energetic tone that shows genuine excitement for the role.",
            "conversational": "Use a friendly, conversational tone while maintaining professionalism."
        }
        
        tone_guide = tone_instructions.get(tone, tone_instructions["professional"])
        
        prompt = f"""You are an expert career coach and professional writer. Generate a compelling cover letter based on the following information.

RESUME:
{resume_content[:4000]}

JOB TITLE: {job_title}
COMPANY: {company_name}

JOB DESCRIPTION:
{job_description[:3000]}

{f"APPLICANT NAME: {user_name}" if user_name else ""}
{f"ADDITIONAL NOTES TO INCLUDE: {additional_notes}" if additional_notes else ""}

TONE INSTRUCTIONS: {tone_guide}

Generate a cover letter that:
1. Opens with an attention-grabbing first paragraph
2. Highlights 2-3 specific achievements from the resume that match the job requirements
3. Shows understanding of the company and role
4. Demonstrates enthusiasm for the opportunity
5. Ends with a confident call to action

IMPORTANT GUIDELINES:
- Keep it to 3-4 paragraphs (around 300-400 words)
- Use specific examples and numbers from the resume where possible
- Avoid generic phrases like "I am writing to apply for..."
- Don't repeat the resume - instead, expand on key achievements
- Make it personal and authentic

Return the cover letter in this exact JSON format:
{{
    "cover_letter": "The full cover letter text with proper formatting and paragraphs",
    "key_points": ["Point 1 highlighted", "Point 2 highlighted", "Point 3 highlighted"],
    "opening_hook": "A brief description of the opening strategy used"
}}

Return ONLY valid JSON, no other text."""

        try:
            openai_client = get_openai_client()
            if not openai_client:
                return {
                    "success": False,
                    "error": "OpenAI API key not configured",
                    "cover_letter": "",
                    "key_points": []
                }
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cover letter writer. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean up the response
            if result.startswith("```json"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            
            import json
            data = json.loads(result)
            
            return {
                "success": True,
                "cover_letter": data.get("cover_letter", ""),
                "key_points": data.get("key_points", []),
                "opening_hook": data.get("opening_hook", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cover_letter": "",
                "key_points": []
            }
    
    @staticmethod
    def refine(
        original_letter: str,
        feedback: str
    ) -> dict:
        """
        Refine an existing cover letter based on feedback
        
        Args:
            original_letter: The original cover letter
            feedback: User's feedback on what to change
        
        Returns:
            dict with refined 'cover_letter'
        """
        
        prompt = f"""Refine this cover letter based on the feedback provided.

ORIGINAL COVER LETTER:
{original_letter}

FEEDBACK/CHANGES REQUESTED:
{feedback}

Generate an improved version of the cover letter that addresses the feedback while maintaining professional quality.

Return ONLY the refined cover letter text, no other commentary."""

        try:
            openai_client = get_openai_client()
            if not openai_client:
                return {
                    "success": False,
                    "error": "OpenAI API key not configured",
                    "cover_letter": original_letter
                }
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cover letter writer. Refine the letter based on feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "cover_letter": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cover_letter": original_letter
            }
