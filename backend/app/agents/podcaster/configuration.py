"""
Podcaster agent configuration for HERO Evidence Library.

This module defines the runtime configuration for podcast generation,
adapted for academic and scientific content.
"""

from typing import Annotated, Optional
from langchain_core.runnables import RunnableConfig, ensure_config
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class Configuration(BaseModel):
    """
    Configuration schema for the podcaster agent.
    
    Attributes:
        podcast_title: Title for the generated podcast
        search_space_id: User's search space identifier
        user_prompt: Optional customization instructions from user
        style: Podcast style (conversational, formal, educational)
        length: Target length (short: 5min, medium: 10min, long: 15min+)
    """
    
    podcast_title: str = Field(
        default="HERO Research Podcast",
        description="Title for the generated podcast"
    )
    
    search_space_id: int = Field(
        ...,
        description="Search space ID for the podcast"
    )
    
    user_prompt: Optional[str] = Field(
        default=None,
        description="User's custom instructions for podcast style/content"
    )
    
    style: str = Field(
        default="conversational",
        description="Podcast style: conversational, formal, or educational"
    )
    
    length: str = Field(
        default="medium",
        description="Target length: short (5min), medium (10min), or long (15min+)"
    )
    
    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """
        Extract Configuration from a RunnableConfig object.
        
        Args:
            config: LangGraph RunnableConfig containing configurable parameters
            
        Returns:
            Configuration object with extracted parameters
        """
        config = ensure_config(config)
        configurable = config.get("configurable", {})
        
        return cls(
            podcast_title=configurable.get("podcast_title", "HERO Research Podcast"),
            search_space_id=configurable["search_space_id"],
            user_prompt=configurable.get("user_prompt"),
            style=configurable.get("style", "conversational"),
            length=configurable.get("length", "medium"),
        )
