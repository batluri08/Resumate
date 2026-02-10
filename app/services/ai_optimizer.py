"""
AI Optimizer Service - Uses OpenAI to optimize resume content for job descriptions
"""

import os
import json
import re
from openai import AsyncOpenAI
from typing import Tuple, List, Dict


class AIOptimizer:
    """Optimize resume content using AI"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in your .env file."
            )
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Load OpenAI configuration from environment variables
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    
    async def optimize(
        self, 
        resume_content: str, 
        job_description: str,
        profile_context: str = ""
    ) -> Tuple[str, List[str]]:
        """
        Optimize resume content for a specific job description.
        Returns changes as find/replace pairs for precise application.
        """
        
        system_prompt = """You are an expert ATS resume optimization specialist. Your job is to make PRECISE, TARGETED changes to help a resume pass ATS screening and appeal to recruiters.

## YOUR TASK
Analyze the job description, identify KEY requirements, then make strategic changes to the resume.

## STEP 1: ANALYZE JOB REQUIREMENTS
Extract from the job description:
- REQUIRED technical skills (languages, frameworks, tools, platforms)
- KEY action verbs and terminology used
- Domain-specific keywords
- Responsibilities that match resume experience

## STEP 2: AUDIT THE RESUME
For each job requirement, check if the resume ALREADY contains:
- The exact keyword
- A synonym or variation (e.g., "ML" vs "Machine Learning")
- Related experience that uses different words

## STEP 3: MAKE CHANGES

### SKILLS SECTION RULES:

**CATEGORIZATION IS CRITICAL:**
- LANGUAGES = Programming/scripting languages ONLY: Python, Java, SQL, JavaScript, Go, Rust, C++, R, TypeScript, Scala, etc.
- FRAMEWORKS/LIBRARIES = Software frameworks: React, Django, Flask, Spring, TensorFlow, PyTorch, Pandas, Node.js, etc.  
- TOOLS/PLATFORMS = Infrastructure & DevOps: AWS, Azure, GCP, Kubernetes, Docker, Terraform, Jenkins, Git, Airflow, Kafka, etc.
- DATABASES = Data stores: PostgreSQL, MySQL, MongoDB, Redis, Snowflake, BigQuery, etc.

**COMMON MISTAKES TO AVOID:**
❌ Terraform in Languages → ✅ Terraform in Tools/Platforms
❌ Kubernetes in Languages → ✅ Kubernetes in Tools/Platforms  
❌ Docker in Languages → ✅ Docker in Tools/Platforms
❌ AWS/GCP/Azure in Languages → ✅ AWS/GCP/Azure in Tools/Platforms
❌ Spark in Languages → ✅ Spark in Tools/Frameworks

**BEFORE ADDING A SKILL:**
1. Search the ENTIRE resume - is it already there in ANY section?
2. If YES → DO NOT add it again, skip this skill
3. If NO → Find the correct category and add it

**WHEN ADDING SKILLS:**
- Find a less relevant skill in the CORRECT category to replace
- Keep the EXACT same format (commas, spacing, line length)
- Replacement must be SAME LENGTH or slightly shorter

### EXPERIENCE SECTION RULES:

**MAKE MORE CHANGES TO EXPERIENCE - This is where ATS matching really matters!**

**WHAT TO LOOK FOR:**
1. Action verbs: Does job say "developed" but resume says "built"? Swap it.
2. Technical terms: Job says "data pipelines", resume says "data workflows"? Swap it.
3. Metrics language: Job emphasizes "scale" or "performance"? Add if missing.
4. Domain terms: Job mentions "ETL", "ML models", "microservices"? Ensure resume uses same terms.

**CHANGE STRATEGY:**
- Swap 1-3 words per bullet point to match job language
- Prioritize bullets that describe SIMILAR work to job requirements
- Keep bullet structure and approximate length the same
- Preserve metrics and specific achievements

**EXAMPLES OF GOOD EXPERIENCE CHANGES:**
- "Built data workflows" → "Built data pipelines" (job says "pipelines")
- "Developed ML systems" → "Developed ML models" (job says "models")
- "Worked with cross-functional teams" → "Collaborated with cross-functional teams" (job emphasizes "collaboration")
- "Created automated tests" → "Implemented automated testing" (job says "testing")
- "Managed cloud resources" → "Managed AWS infrastructure" (job specifically mentions AWS)

**WHAT NOT TO CHANGE:**
- Bullet already uses the exact job terminology
- Bullet describes completely unrelated work
- Changing would lose important metrics or specifics

## OUTPUT FORMAT

Return ONLY valid JSON:
{
  "changes": [
    {
      "find": "EXACT text from resume (copy precisely including punctuation)",
      "replace": "Modified text (same or shorter length)",
      "reason": "Brief explanation"
    }
  ],
  "key_insights": "2-3 sentence summary of main optimizations made"
}

## CRITICAL RULES
1. NEVER add a skill that's already in the resume (search carefully!)
2. Put skills in the CORRECT category (Terraform/K8s/Docker = Tools, NOT Languages)
3. Make 3-6 changes to experience section - this is important for ATS
4. Keep replacements SAME LENGTH or shorter
5. Copy the "find" text EXACTLY as it appears (including bullet characters, spacing)"""

        # Build profile section if provided
        profile_section = ""
        if profile_context:
            profile_section = f"""
## USER PREFERENCES
{profile_context}
Respect these preferences: keep must-have skills, focus on target role keywords.
"""

        user_prompt = f"""Optimize this resume for the job description below.
{profile_section}
## IMPORTANT REMINDERS
1. CHECK if each skill already exists before adding (search whole resume!)
2. Put infrastructure tools (Terraform, K8s, Docker, AWS) in Tools/Platforms, NOT Languages
3. Make meaningful changes to 3-6 experience bullet points
4. Keep exact same formatting and line lengths

## JOB DESCRIPTION
{job_description}

## RESUME CONTENT
{resume_content}

Return your changes as JSON. Make sure to:
- Search the resume for existing skills before adding
- Place skills in correct categories
- Make several experience changes using job terminology"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result = response.choices[0].message.content
            
            # Parse and validate the JSON response
            changes, suggestions = self._parse_and_validate_response(result, resume_content)
            
            return changes, suggestions
            
        except Exception as e:
            raise Exception(f"AI optimization failed: {str(e)}")
    
    def _parse_and_validate_response(self, response: str, original_content: str) -> Tuple[List[Dict], List[str]]:
        """Parse the JSON response and validate changes against original content"""
        
        changes = []
        suggestions = []
        
        # Extract JSON from response (might be wrapped in markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_str = response.strip()
        
        try:
            data = json.loads(json_str)
            
            if "changes" in data:
                original_lower = original_content.lower()
                
                for change in data["changes"]:
                    if "find" not in change or "replace" not in change:
                        continue
                    
                    find_text = change["find"]
                    replace_text = change["replace"]
                    reason = change.get("reason", "")
                    
                    # Validation 1: Check if "find" text actually exists in resume
                    if find_text not in original_content:
                        print(f"[DEBUG] Skipping change - text not found: '{find_text[:50]}...'")
                        continue
                    
                    # Validation 2: Allow new words even if they exist elsewhere in the resume
                    # (Relaxed: do not skip changes if new words already exist)
                    # Validation 3: Allow up to 50% longer replacements
                    if len(replace_text) > len(find_text) * 1.5:  # Allow 50% longer max
                        print(f"[DEBUG] Trimming replacement that's too long")
                        replace_text = replace_text[:int(len(find_text) * 1.5)]
                    
                    changes.append({
                        "find": find_text,
                        "replace": replace_text,
                        "reason": reason
                    })
                    
                    if reason:
                        suggestions.append(reason)
            
            if "key_insights" in data:
                suggestions.insert(0, data["key_insights"])
                
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parse error: {e}")
            print(f"[DEBUG] Response was: {response[:500]}")
            suggestions = ["Could not parse AI response - using original resume"]
        
        print(f"[DEBUG] Validated {len(changes)} changes from AI response")
        for i, c in enumerate(changes[:5]):
            print(f"[DEBUG] Change {i+1}: '{c['find'][:50]}...' -> '{c['replace'][:50]}...'")
        
        return changes, suggestions
