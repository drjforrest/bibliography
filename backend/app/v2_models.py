"""
New database models for HERO Evidence Library v2.0
These models support dynamic content generation features:
- Podcasts
- Summaries
- Infographics
- Slide Decks
"""

# Add these imports at the top of db.py if not already present:
# from sqlalchemy.dialects.postgresql import JSONB

# ============================================================================
# v2.0 Models - Add these after SearchSpace class definition
# ============================================================================


class Podcast(BaseModel, TimestampMixin):
    """
    Generated podcasts from selected papers.
    
    Podcasts are audio conversations between AI hosts discussing research papers.
    Each podcast includes:
    - Transcript with speaker dialogue
    - Audio file (MP3 format)
    - References to source papers
    - User customization options
    """
    __tablename__ = "podcasts"
    
    # Metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Audio duration
    
    # Content
    podcast_transcript = Column(JSON, nullable=True)  # List of {speaker_id, dialog}
    file_location = Column(Text, nullable=True)  # Path or URL to audio file
    file_size_bytes = Column(Integer, nullable=True)
    
    # Source tracking
    source_paper_ids = Column(ARRAY(Integer), nullable=False)  # Papers used
    user_prompt = Column(Text, nullable=True)  # User's customization instructions
    
    # Generation metadata
    generation_status = Column(
        String(50), 
        nullable=False, 
        default="pending",
        index=True
    )  # pending, processing, complete, error
    generation_error = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True, index=True)  # Celery task ID
    
    # Relations
    search_space_id = Column(
        Integer, ForeignKey("searchspaces.id", ondelete="CASCADE"), nullable=False
    )
    search_space = relationship("SearchSpace", back_populates="podcasts")
    
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="podcasts")


class SummaryType(str, Enum):
    """Types of summaries that can be generated"""
    LAY = "lay"  # Accessible to general audiences
    TECHNICAL = "technical"  # For peer researchers
    EXECUTIVE = "executive"  # Decision-maker focused
    COMPARATIVE = "comparative"  # Multi-paper synthesis
    VISUAL = "visual"  # Structured for infographic generation


class Summary(BaseModel, TimestampMixin):
    """
    AI-generated summaries of research papers.
    
    Summaries can be:
    - Single-paper summaries (different styles)
    - Multi-paper comparative summaries
    - Structured for different audiences
    """
    __tablename__ = "summaries"
    
    # Metadata
    title = Column(String(500), nullable=False)
    summary_type = Column(
        SQLAlchemyEnum(SummaryType), 
        nullable=False,
        index=True
    )
    
    # Content
    content = Column(Text, nullable=False)
    key_findings = Column(JSON, nullable=True)  # Structured findings
    
    # Source tracking
    source_paper_ids = Column(ARRAY(Integer), nullable=False)
    user_prompt = Column(Text, nullable=True)
    
    # Generation metadata
    generation_status = Column(
        String(50), 
        nullable=False, 
        default="pending"
    )
    generation_error = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True, index=True)
    
    # Relations
    search_space_id = Column(
        Integer, ForeignKey("searchspaces.id", ondelete="CASCADE"), nullable=True
    )
    search_space = relationship("SearchSpace", back_populates="summaries")
    
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="summaries")


class Infographic(BaseModel, TimestampMixin):
    """
    Generated visual content from research papers.
    
    Infographics transform research findings into visual formats:
    - Charts and graphs
    - Process diagrams
    - Timeline visualizations
    - Comparison matrices
    """
    __tablename__ = "infographics"
    
    # Metadata
    title = Column(String(500), nullable=False)
    infographic_type = Column(
        String(50), 
        nullable=False
    )  # chart, diagram, timeline, matrix
    
    # Content
    file_location = Column(Text, nullable=True)  # SVG/PNG file path
    file_format = Column(String(10), nullable=True)  # svg, png
    file_size_bytes = Column(Integer, nullable=True)
    
    # Structured data used for generation
    data_json = Column(JSON, nullable=True)
    
    # Source tracking
    source_paper_ids = Column(ARRAY(Integer), nullable=False)
    user_prompt = Column(Text, nullable=True)
    
    # Generation metadata
    generation_status = Column(String(50), nullable=False, default="pending")
    generation_error = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True, index=True)
    
    # Relations
    search_space_id = Column(
        Integer, ForeignKey("searchspaces.id", ondelete="CASCADE"), nullable=True
    )
    search_space = relationship("SearchSpace", back_populates="infographics")
    
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="infographics")


class SlideDeck(BaseModel, TimestampMixin):
    """
    Generated presentation slide decks from research papers.
    
    Slide decks are created for:
    - Research presentations
    - Teaching materials
    - Conference talks
    - Grant proposals
    """
    __tablename__ = "slide_decks"
    
    # Metadata
    title = Column(String(500), nullable=False)
    slide_count = Column(Integer, nullable=True)
    
    # Content
    file_location = Column(Text, nullable=True)  # PPTX/PDF file path
    file_format = Column(String(10), nullable=True)  # pptx, pdf
    file_size_bytes = Column(Integer, nullable=True)
    
    # Slide structure (JSON)
    slides_json = Column(JSON, nullable=True)  # Array of slide objects
    
    # Source tracking
    source_paper_ids = Column(ARRAY(Integer), nullable=False)
    user_prompt = Column(Text, nullable=True)
    
    # Generation metadata
    generation_status = Column(String(50), nullable=False, default="pending")
    generation_error = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True, index=True)
    
    # Relations
    search_space_id = Column(
        Integer, ForeignKey("searchspaces.id", ondelete="CASCADE"), nullable=True
    )
    search_space = relationship("SearchSpace", back_populates="slide_decks")
    
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="slide_decks")


# ============================================================================
# Update existing models to add relationships
# ============================================================================

# Add these to SearchSpace class:
#     podcasts = relationship(
#         "Podcast",
#         back_populates="search_space",
#         order_by="Podcast.created_at.desc()",
#         cascade="all, delete-orphan",
#     )
#     summaries = relationship(
#         "Summary",
#         back_populates="search_space",
#         order_by="Summary.created_at.desc()",
#         cascade="all, delete-orphan",
#     )
#     infographics = relationship(
#         "Infographic",
#         back_populates="search_space",
#         order_by="Infographic.created_at.desc()",
#         cascade="all, delete-orphan",
#     )
#     slide_decks = relationship(
#         "SlideDeck",
#         back_populates="search_space",
#         order_by="SlideDeck.created_at.desc()",
#         cascade="all, delete-orphan",
#     )

# Add these to User class:
#     podcasts = relationship("Podcast", back_populates="user")
#     summaries = relationship("Summary", back_populates="user")
#     infographics = relationship("Infographic", back_populates="user")
#     slide_decks = relationship("SlideDeck", back_populates="user")
