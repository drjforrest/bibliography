"""
State management for the podcaster agent.

Defines the Pydantic models for podcast transcript entries and the overall
state passed through the LangGraph workflow.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class PodcastTranscriptEntry(BaseModel):
    """
    A single dialogue entry in the podcast transcript.
    
    Attributes:
        speaker_id: 0 for Host 1 (primary), 1 for Host 2 (secondary)
        dialog: The spoken text for this entry
    """
    speaker_id: int = Field(
        ...,
        description="Speaker identifier: 0=Host 1, 1=Host 2"
    )
    dialog: str = Field(
        ...,
        description="The dialogue text to be spoken"
    )


class PodcastTranscripts(BaseModel):
    """
    Collection of podcast transcript entries.
    
    This is the format expected from the LLM when generating transcripts.
    """
    podcast_transcripts: List[PodcastTranscriptEntry] = Field(
        default_factory=list,
        description="List of dialogue entries forming the podcast"
    )


class State(BaseModel):
    """
    State object passed through the podcaster LangGraph workflow.
    
    The state accumulates data as it flows through nodes:
    1. source_content → input research content
    2. podcast_transcript → generated dialogue
    3. final_podcast_file_path → completed audio file
    """
    
    # Input
    source_content: str = Field(
        ...,
        description="Research paper content to convert into podcast"
    )
    
    db_session: Any = Field(
        default=None,
        description="Database session for accessing models"
    )
    
    # Generated during workflow
    podcast_transcript: Optional[List[PodcastTranscriptEntry]] = Field(
        default=None,
        description="Generated podcast dialogue entries"
    )
    
    final_podcast_file_path: Optional[str] = Field(
        default=None,
        description="Path to the final merged audio file"
    )
    
    class Config:
        arbitrary_types_allowed = True  # Allow AsyncSession type
