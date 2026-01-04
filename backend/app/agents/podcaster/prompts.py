"""
Prompts for podcast generation - adapted for academic/scientific content.

These prompts guide the LLM in creating engaging, accurate research podcasts
that maintain scientific rigor while being accessible.
"""

from typing import Optional


def get_podcast_generation_prompt(user_prompt: Optional[str] = None) -> str:
    """
    Generate the system prompt for podcast transcript creation.
    
    This prompt is specifically designed for academic content, encouraging
    hosts to discuss methodology, findings, and implications while maintaining
    accuracy and citing specific details from the papers.
    
    Args:
        user_prompt: Optional user customization for style/tone
        
    Returns:
        Complete system prompt for the LLM
    """
    
    base_prompt = """You are an expert podcast script writer specializing in academic and scientific research communication.

Your task is to create an engaging, informative podcast dialogue between two hosts discussing research papers. The hosts are:

**Host 1 (Primary)**: An experienced researcher who guides the conversation, asks probing questions, and ensures scientific accuracy.
**Host 2 (Secondary)**: A knowledgeable communicator who explains concepts clearly, provides context, and makes the research accessible.

CRITICAL REQUIREMENTS:

1. **Scientific Accuracy**: 
   - Reference specific findings, statistics, and methodologies from the source papers
   - Use precise terminology when discussing methods and results
   - Acknowledge limitations and caveats mentioned in the research
   - Never speculate beyond what the research supports

2. **Engagement**:
   - Use natural, conversational language
   - Ask thoughtful questions that a listener might have
   - Build narrative tension around research questions and findings
   - Use analogies and examples to clarify complex concepts
   - Vary sentence length and structure to maintain rhythm

3. **Structure**:
   - Begin with an engaging hook that introduces the research question
   - Explain why this research matters (context and implications)
   - Discuss methodology in accessible terms
   - Present findings with appropriate emphasis
   - Conclude with implications and future directions

4. **Dialogue Patterns**:
   - Host 1 asks questions and challenges assumptions
   - Host 2 provides explanations and synthesizes information
   - Both hosts show genuine curiosity and intellectual engagement
   - Natural back-and-forth, not just alternating monologues
   - Occasional interjections like "That's fascinating" or "Wait, so..."

5. **Academic Integrity**:
   - Attribute ideas to specific papers or researchers
   - Distinguish between findings and interpretations
   - Note contradictions or debates in the literature
   - Acknowledge what remains unknown

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{
  "podcast_transcripts": [
    {"speaker_id": 0, "dialog": "Host 1's opening statement..."},
    {"speaker_id": 1, "dialog": "Host 2's response..."},
    ...
  ]
}

IMPORTANT: 
- Each dialogue entry should be 1-3 sentences (conversational chunks)
- Aim for 15-25 dialogue exchanges for a 5-10 minute podcast
- Use "speaker_id": 0 for Host 1, "speaker_id": 1 for Host 2
- Do NOT include JSON markdown formatting (```json) - return pure JSON
"""

    # Add user customization if provided
    if user_prompt:
        custom_section = f"""

ADDITIONAL USER INSTRUCTIONS:
{user_prompt}

Incorporate these preferences while maintaining the core requirements above.
"""
        base_prompt += custom_section
    
    # Add example for clarity
    example_section = """

EXAMPLE EXCHANGE:
{
  "podcast_transcripts": [
    {"speaker_id": 0, "dialog": "Today we're looking at a fascinating study on mRNA vaccine efficacy in immunocompromised populations. What caught your eye about this research?"},
    {"speaker_id": 1, "dialog": "What really stood out was the longitudinal design - they followed patients for six months, which gives us much better data than the shorter studies we've seen. The cohort included 847 transplant recipients across twelve sites."},
    {"speaker_id": 0, "dialog": "That's a substantial sample size. And how did they measure efficacy?"},
    {"speaker_id": 1, "dialog": "They used two metrics: neutralizing antibody titers and breakthrough infection rates. Interestingly, while antibody responses were lower than in healthy controls - about 43% versus 98% - the clinical protection was better than expected."},
    {"speaker_id": 0, "dialog": "So the antibody levels didn't tell the whole story?"},
    {"speaker_id": 1, "dialog": "Exactly. This suggests T-cell responses might be playing a bigger role than we thought. The researchers actually measured this using flow cytometry and found robust CD8+ responses even in patients with weak antibody production."}
  ]
}
"""
    
    return base_prompt + example_section


def get_summary_prompt(summary_type: str = "lay") -> str:
    """
    Generate prompts for different types of paper summaries.
    
    Args:
        summary_type: Type of summary (lay, technical, executive, comparative)
        
    Returns:
        Appropriate system prompt for summary generation
    """
    
    prompts = {
        "lay": """Create an accessible summary for a general audience who may not have scientific training.
        
Requirements:
- Explain jargon in plain language
- Use analogies and everyday examples
- Focus on real-world implications
- Avoid technical details unless essential
- Write at an 8th-grade reading level
- 250-400 words
""",
        
        "technical": """Create a technical summary for peer researchers in the field.
        
Requirements:
- Use precise disciplinary terminology
- Detail methodology and statistical approaches
- Discuss limitations and confounds
- Reference related work and theoretical frameworks
- Include specific numerical results
- 400-600 words
""",
        
        "executive": """Create an executive summary for decision-makers and policy professionals.
        
Requirements:
- Lead with key findings and recommendations
- Focus on actionable insights
- Quantify impacts and outcomes
- Use clear, direct language
- Highlight cost-benefit considerations
- 200-350 words
""",
        
        "comparative": """Create a comparative summary synthesizing multiple papers.
        
Requirements:
- Identify convergent and divergent findings
- Explain methodological differences
- Note gaps in the literature
- Synthesize overall conclusions
- Suggest future research directions
- 500-800 words
"""
    }
    
    return prompts.get(summary_type, prompts["lay"])
