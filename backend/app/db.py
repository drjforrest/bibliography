from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from enum import Enum
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Date,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
    text,
    TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, relationship

from app.config import config
from app.retriver.chunks_hybrid_search import ChucksHybridSearchRetriever
from app.retriver.documents_hybrid_search import DocumentHybridSearchRetriever

if config.AUTH_TYPE == "GOOGLE":
    from fastapi_users.db import (
        SQLAlchemyBaseOAuthAccountTableUUID,
        SQLAlchemyBaseUserTableUUID,
        SQLAlchemyUserDatabase,
    )
else:
    from fastapi_users.db import (
        SQLAlchemyBaseUserTableUUID,
        SQLAlchemyUserDatabase,
    )

DATABASE_URL = config.DATABASE_URL


class DocumentType(str, Enum):
    EXTENSION = "EXTENSION"
    CRAWLED_URL = "CRAWLED_URL"
    FILE = "FILE"
    SLACK_CONNECTOR = "SLACK_CONNECTOR"
    NOTION_CONNECTOR = "NOTION_CONNECTOR"
    YOUTUBE_VIDEO = "YOUTUBE_VIDEO"
    GITHUB_CONNECTOR = "GITHUB_CONNECTOR"
    LINEAR_CONNECTOR = "LINEAR_CONNECTOR"
    SCIENTIFIC_PAPER = "SCIENTIFIC_PAPER"

class SearchSourceConnectorType(str, Enum):
    SERPER_API = "SERPER_API" # NOT IMPLEMENTED YET : DON'T REMEMBER WHY : MOST PROBABLY BECAUSE WE NEED TO CRAWL THE RESULTS RETURNED BY IT
    TAVILY_API = "TAVILY_API"
    LINKUP_API = "LINKUP_API"
    SLACK_CONNECTOR = "SLACK_CONNECTOR"
    NOTION_CONNECTOR = "NOTION_CONNECTOR"
    GITHUB_CONNECTOR = "GITHUB_CONNECTOR"
    LINEAR_CONNECTOR = "LINEAR_CONNECTOR"
    
class ChatType(str, Enum):
    GENERAL = "GENERAL"
    DEEP = "DEEP"
    DEEPER = "DEEPER"
    DEEPEST = "DEEPEST"
    
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)

class Chat(BaseModel, TimestampMixin):
    __tablename__ = "chats"

    type = Column(SQLAlchemyEnum(ChatType), nullable=False)
    title = Column(String, nullable=False, index=True)
    initial_connectors = Column(ARRAY(String), nullable=True)
    messages = Column(JSON, nullable=False)
    
    search_space_id = Column(Integer, ForeignKey('searchspaces.id', ondelete='CASCADE'), nullable=False)
    search_space = relationship('SearchSpace', back_populates='chats')

class Document(BaseModel, TimestampMixin):
    __tablename__ = "documents"
    
    title = Column(String, nullable=False, index=True)
    document_type = Column(SQLAlchemyEnum(DocumentType), nullable=False)
    document_metadata = Column(JSON, nullable=True)
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(config.embedding_model_instance.dimension))
    
    search_space_id = Column(Integer, ForeignKey("searchspaces.id", ondelete='CASCADE'), nullable=False)
    search_space = relationship("SearchSpace", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    scientific_paper = relationship("ScientificPaper", back_populates="document", uselist=False, cascade="all, delete-orphan")

class Chunk(BaseModel, TimestampMixin):
    __tablename__ = "chunks"
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(config.embedding_model_instance.dimension))
    
    document_id = Column(Integer, ForeignKey("documents.id", ondelete='CASCADE'), nullable=False)
    document = relationship("Document", back_populates="chunks")

class ScientificPaper(BaseModel, TimestampMixin):
    __tablename__ = "scientific_papers"
    
    # Basic bibliographic information
    title = Column(String, nullable=False, index=True)
    authors = Column(ARRAY(String), nullable=True)  # List of author names
    journal = Column(String, nullable=True, index=True)
    volume = Column(String, nullable=True)
    issue = Column(String, nullable=True)
    pages = Column(String, nullable=True)  # e.g., "123-145" or "e12345"
    publication_date = Column(Date, nullable=True, index=True)
    publication_year = Column(Integer, nullable=True, index=True)
    
    # Identifiers
    doi = Column(String, nullable=True, unique=True, index=True)
    pmid = Column(String, nullable=True, unique=True, index=True)  # PubMed ID
    arxiv_id = Column(String, nullable=True, unique=True, index=True)
    isbn = Column(String, nullable=True)
    issn = Column(String, nullable=True)
    
    # Content
    abstract = Column(Text, nullable=True)
    lay_summary = Column(Text, nullable=True)  # AI-generated lay summary for general audiences
    keywords = Column(ARRAY(String), nullable=True)
    full_text = Column(Text, nullable=True)  # Extracted PDF text
    
    # File information
    file_path = Column(String, nullable=False)  # Path to PDF file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    file_hash = Column(String, nullable=True, index=True)  # SHA256 hash for deduplication
    
    # Citation and reference information
    citation_count = Column(Integer, nullable=True, default=0)
    references = Column(JSON, nullable=True)  # List of cited papers
    cited_by = Column(JSON, nullable=True)  # Papers that cite this one
    
    # Categories and subjects
    subject_areas = Column(ARRAY(String), nullable=True)  # Research areas/fields
    tags = Column(ARRAY(String), nullable=True)  # User-defined tags
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True)  # Extraction confidence
    is_open_access = Column(Boolean, nullable=True, default=False)
    
    # Processing status
    processing_status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    extraction_metadata = Column(JSON, nullable=True)  # Metadata about extraction process
    
    # DEVONthink source tracking
    dt_source_uuid = Column(String(255), nullable=True, index=True)  # DEVONthink source UUID
    dt_source_path = Column(Text, nullable=True)  # DEVONthink source path
    
    # Relations
    document_id = Column(Integer, ForeignKey("documents.id", ondelete='CASCADE'), nullable=False)
    document = relationship("Document", back_populates="scientific_paper")

    annotations = relationship("PaperAnnotation", back_populates="paper", cascade="all, delete-orphan")
    tag_objects = relationship("Tag", secondary="paper_tags", back_populates="papers")

class PaperAnnotation(BaseModel, TimestampMixin):
    __tablename__ = "paper_annotations"

    # Annotation content
    content = Column(Text, nullable=False)
    annotation_type = Column(String, nullable=False, default="note")  # note, highlight, bookmark

    # Location in PDF
    page_number = Column(Integer, nullable=True)
    x_coordinate = Column(Float, nullable=True)
    y_coordinate = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)

    # Metadata
    color = Column(String, nullable=True)  # For highlights
    is_private = Column(Boolean, nullable=False, default=True)

    # Relations
    paper_id = Column(Integer, ForeignKey("scientific_papers.id", ondelete='CASCADE'), nullable=False)
    paper = relationship("ScientificPaper", back_populates="annotations")

    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User")

# Many-to-many association table for papers and tags
paper_tags = Table(
    'paper_tags',
    Base.metadata,
    Column('paper_id', Integer, ForeignKey('scientific_papers.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
)

class Tag(BaseModel, TimestampMixin):
    __tablename__ = "tags"

    # Tag information
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True, default="#3B82F6")  # Hex color code
    icon = Column(String(50), nullable=True)  # Material icon name

    # Hierarchy support
    parent_id = Column(Integer, ForeignKey("tags.id", ondelete='CASCADE'), nullable=True, index=True)
    parent = relationship("Tag", remote_side="Tag.id", backref="children")

    # User ownership
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False, index=True)
    user = relationship("User", back_populates="tags")

    # Many-to-many relationship with papers
    papers = relationship("ScientificPaper", secondary=paper_tags, back_populates="tag_objects")

class Podcast(BaseModel, TimestampMixin):
    __tablename__ = "podcasts"
    
    title = Column(String, nullable=False, index=True)
    podcast_transcript = Column(JSON, nullable=False, default={})
    file_location = Column(String(500), nullable=False, default="")
    
    search_space_id = Column(Integer, ForeignKey("searchspaces.id", ondelete='CASCADE'), nullable=False)
    search_space = relationship("SearchSpace", back_populates="podcasts")
    
class SearchSpace(BaseModel, TimestampMixin):
    __tablename__ = "searchspaces"
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="search_spaces")
    
    documents = relationship("Document", back_populates="search_space", order_by="Document.id", cascade="all, delete-orphan")
    podcasts = relationship("Podcast", back_populates="search_space", order_by="Podcast.id", cascade="all, delete-orphan")
    chats = relationship('Chat', back_populates='search_space', order_by='Chat.id', cascade="all, delete-orphan")
    
class SearchSourceConnector(BaseModel, TimestampMixin):
    __tablename__ = "search_source_connectors"
    
    name = Column(String(100), nullable=False, index=True)
    connector_type = Column(SQLAlchemyEnum(SearchSourceConnectorType), nullable=False, unique=True)
    is_indexable = Column(Boolean, nullable=False, default=False)
    last_indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    config = Column(JSON, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="search_source_connectors")

class DevonthinkSyncStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    ERROR = "error"
    UPDATED = "updated"

class DevonthinkSync(BaseModel, TimestampMixin):
    __tablename__ = "devonthink_sync"
    
    # DEVONthink identifiers
    dt_uuid = Column(String(255), unique=True, nullable=False, index=True)  # DEVONthink UUID
    dt_path = Column(Text, nullable=True)  # DEVONthink location path
    dt_modified_date = Column(TIMESTAMP(timezone=True), nullable=True)  # Last modified in DT
    
    # Local identifiers
    local_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)  # Local paper UUID
    
    # Sync tracking
    last_sync_date = Column(TIMESTAMP(timezone=True), nullable=True)  # Last sync to our system
    sync_status = Column(SQLAlchemyEnum(DevonthinkSyncStatus), nullable=False, default=DevonthinkSyncStatus.PENDING)
    error_message = Column(Text, nullable=True)  # Error details if sync failed
    
    # Relations
    scientific_paper_id = Column(Integer, ForeignKey("scientific_papers.id", ondelete='CASCADE'), nullable=True)
    scientific_paper = relationship("ScientificPaper")
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="devonthink_syncs")

class DevonthinkFolder(BaseModel, TimestampMixin):
    __tablename__ = "devonthink_folders"
    
    # DEVONthink folder identifiers
    dt_uuid = Column(String(255), unique=True, nullable=False, index=True)  # DEVONthink folder UUID
    dt_path = Column(Text, nullable=False, index=True)  # DEVONthink location path
    folder_name = Column(String, nullable=False)
    
    # Hierarchy
    parent_dt_uuid = Column(String(255), nullable=True, index=True)  # Parent folder UUID
    depth_level = Column(Integer, nullable=False, default=0)  # Depth in hierarchy
    
    # Sync tracking
    sync_status = Column(SQLAlchemyEnum(DevonthinkSyncStatus), nullable=False, default=DevonthinkSyncStatus.PENDING)
    last_sync_date = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relations
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="devonthink_folders")

if config.AUTH_TYPE == "GOOGLE":
    class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
        pass


    class User(SQLAlchemyBaseUserTableUUID, Base):
        oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
            "OAuthAccount", lazy="joined"
        )
        search_spaces = relationship("SearchSpace", back_populates="user")
        search_source_connectors = relationship("SearchSourceConnector", back_populates="user")
        devonthink_syncs = relationship("DevonthinkSync", back_populates="user")
        devonthink_folders = relationship("DevonthinkFolder", back_populates="user")
        tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
else:
    class User(SQLAlchemyBaseUserTableUUID, Base):

        search_spaces = relationship("SearchSpace", back_populates="user")
        search_source_connectors = relationship("SearchSourceConnector", back_populates="user")
        devonthink_syncs = relationship("DevonthinkSync", back_populates="user")
        devonthink_folders = relationship("DevonthinkFolder", back_populates="user")
        tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        

async def setup_indexes():
    async with engine.begin() as conn:
        # Create indexes 
        # Document Summary Indexes
        await conn.execute(text('CREATE INDEX IF NOT EXISTS document_vector_index ON documents USING hnsw (embedding public.vector_cosine_ops)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS document_search_index ON documents USING gin (to_tsvector(\'english\', content))'))
        # Document Chuck Indexes
        await conn.execute(text('CREATE INDEX IF NOT EXISTS chucks_vector_index ON chunks USING hnsw (embedding public.vector_cosine_ops)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS chucks_search_index ON chunks USING gin (to_tsvector(\'english\', content))'))

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        await conn.run_sync(Base.metadata.create_all)
    await setup_indexes()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


if config.AUTH_TYPE == "GOOGLE":
    async def get_user_db(session: AsyncSession = Depends(get_async_session)):
        yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
else:
    async def get_user_db(session: AsyncSession = Depends(get_async_session)):
        yield SQLAlchemyUserDatabase(session, User)
    
async def get_chucks_hybrid_search_retriever(session: AsyncSession = Depends(get_async_session)):
    return ChucksHybridSearchRetriever(session)

async def get_documents_hybrid_search_retriever(session: AsyncSession = Depends(get_async_session)):
    return DocumentHybridSearchRetriever(session)
