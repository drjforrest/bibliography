"""
Utility functions for podcast generation.

Includes voice selection, audio processing helpers, and file management.
"""

import os
from typing import Literal


def get_voice_for_provider(
    provider: str, 
    speaker_id: int
) -> str:
    """
    Select appropriate voice for the TTS provider and speaker.
    
    Args:
        provider: TTS provider identifier (e.g., "openai", "local/kokoro")
        speaker_id: 0 for Host 1 (primary), 1 for Host 2 (secondary)
        
    Returns:
        Voice identifier string for the provider
        
    Academic voice selection strategy:
    - Host 1: Warm, authoritative, slightly lower pitch
    - Host 2: Clear, engaging, slightly higher pitch
    - Aim for gender diversity when possible
    """
    
    # OpenAI TTS voices
    if provider == "openai":
        if speaker_id == 0:
            return "alloy"  # Host 1: Warm, balanced
        else:
            return "nova"  # Host 2: Clear, friendly
    
    # Kokoro TTS voices (local)
    elif provider == "local/kokoro":
        if speaker_id == 0:
            return "af_bella"  # Host 1: Professional female voice
        else:
            return "am_adam"  # Host 2: Clear male voice
    
    # ElevenLabs voices
    elif provider == "elevenlabs":
        if speaker_id == 0:
            return "Rachel"  # Host 1: Professional, clear
        else:
            return "Josh"  # Host 2: Conversational, warm
    
    # Fallback
    else:
        return "default"


def estimate_podcast_duration(
    transcript_length: int,
    words_per_minute: int = 150
) -> int:
    """
    Estimate podcast duration in seconds based on transcript.
    
    Args:
        transcript_length: Number of words in transcript
        words_per_minute: Speaking rate (default: 150 wpm for clear explanation)
        
    Returns:
        Estimated duration in seconds
    """
    minutes = transcript_length / words_per_minute
    return int(minutes * 60)


def create_podcast_directory() -> str:
    """
    Ensure podcast storage directory exists.
    
    Returns:
        Path to podcast directory
    """
    podcast_dir = "podcasts"
    os.makedirs(podcast_dir, exist_ok=True)
    return podcast_dir


def format_timestamp(seconds: int) -> str:
    """
    Format seconds into MM:SS timestamp.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted timestamp string
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def validate_transcript(transcript: list) -> bool:
    """
    Validate podcast transcript structure.
    
    Args:
        transcript: List of transcript entries
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(transcript, list):
        return False
    
    for entry in transcript:
        if not isinstance(entry, dict):
            return False
        if "speaker_id" not in entry or "dialog" not in entry:
            return False
        if not isinstance(entry["speaker_id"], int):
            return False
        if entry["speaker_id"] not in [0, 1]:
            return False
        if not isinstance(entry["dialog"], str):
            return False
        if len(entry["dialog"]) == 0:
            return False
    
    return True
