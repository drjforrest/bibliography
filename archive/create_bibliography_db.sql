-- Bibliography Database Schema Creation Script
-- Generated for transfer to mac-mini
-- This script recreates the complete database structure with proper dependency order

-- ========================================
-- 1. CREATE EXTENSIONS
-- ========================================

-- Enable the vector extension for pgvector support
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- ========================================
-- 2. CREATE ENUM TYPES
-- ========================================

-- Document types for the system
CREATE TYPE public.documenttype AS ENUM (
    'EXTENSION',
    'CRAWLED_URL',
    'FILE',
    'SLACK_CONNECTOR',
    'NOTION_CONNECTOR',
    'YOUTUBE_VIDEO',
    'GITHUB_CONNECTOR',
    'LINEAR_CONNECTOR',
    'SCIENTIFIC_PAPER'
);

-- Literature types for scientific papers
CREATE TYPE public.literaturetype AS ENUM (
    'PEER_REVIEWED',
    'GREY_LITERATURE',
    'NEWS'
);

-- Chat types for different conversation modes
CREATE TYPE public.chattype AS ENUM (
    'GENERAL',
    'DEEP',
    'DEEPER',
    'DEEPEST'
);

-- Search source connector types
CREATE TYPE public.searchsourceconnectortype AS ENUM (
    'SERPER_API',
    'TAVILY_API',
    'LINKUP_API',
    'SLACK_CONNECTOR',
    'NOTION_CONNECTOR',
    'GITHUB_CONNECTOR',
    'LINEAR_CONNECTOR'
);

-- DEVONthink sync status types
CREATE TYPE public.devonthinksyncstatus AS ENUM (
    'PENDING',
    'SYNCED',
    'ERROR',
    'UPDATED'
);

-- ========================================
-- 3. CREATE TABLES (in dependency order)
-- ========================================

-- User table (no dependencies)
CREATE TABLE public."user" (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    hashed_password character varying(1024) NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    is_verified boolean NOT NULL
);

-- Search spaces (depends on user)
CREATE TABLE public.searchspaces (
    name character varying(100) NOT NULL,
    description character varying(500),
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Documents (depends on searchspaces)
CREATE TABLE public.documents (
    title character varying NOT NULL,
    document_type public.documenttype NOT NULL,
    document_metadata json,
    content text NOT NULL,
    embedding public.vector(384),
    search_space_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Scientific papers (depends on documents)
CREATE TABLE public.scientific_papers (
    literature_type public.literaturetype NOT NULL DEFAULT 'PEER_REVIEWED',
    title character varying NOT NULL,
    authors character varying[],
    journal character varying,
    volume character varying,
    issue character varying,
    pages character varying,
    publication_date date,
    publication_year integer,
    doi character varying,
    pmid character varying,
    arxiv_id character varying,
    isbn character varying,
    issn character varying,
    abstract text,
    lay_summary text,
    keywords character varying[],
    full_text text,
    file_path character varying NOT NULL,
    file_size integer,
    file_hash character varying,
    citation_count integer DEFAULT 0,
    "references" json,
    cited_by json,
    subject_areas character varying[],
    tags character varying[],
    confidence_score double precision,
    is_open_access boolean DEFAULT false,
    processing_status character varying NOT NULL DEFAULT 'pending',
    extraction_metadata json,
    dt_source_uuid character varying(255),
    dt_source_path text,
    document_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Tags (depends on user)
CREATE TABLE public.tags (
    name character varying(100) NOT NULL,
    description text,
    color character varying(20) DEFAULT '#3B82F6',
    icon character varying(50),
    parent_id integer,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Chunks (depends on documents)
CREATE TABLE public.chunks (
    content text NOT NULL,
    embedding public.vector(384),
    document_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Chats (depends on searchspaces)
CREATE TABLE public.chats (
    type public.chattype NOT NULL,
    title character varying NOT NULL,
    initial_connectors character varying[],
    messages json NOT NULL,
    search_space_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Podcasts (depends on searchspaces)
CREATE TABLE public.podcasts (
    title character varying NOT NULL,
    podcast_transcript json NOT NULL DEFAULT '{}',
    file_location character varying(500) NOT NULL DEFAULT '',
    search_space_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Search source connectors (depends on user)
CREATE TABLE public.search_source_connectors (
    name character varying(100) NOT NULL,
    connector_type public.searchsourceconnectortype NOT NULL,
    is_indexable boolean NOT NULL DEFAULT false,
    last_indexed_at timestamp with time zone,
    config json NOT NULL,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- DEVONthink sync (depends on user and scientific_papers)
CREATE TABLE public.devonthink_sync (
    dt_uuid character varying(255) NOT NULL,
    dt_path text,
    dt_modified_date timestamp with time zone,
    local_uuid uuid NOT NULL,
    last_sync_date timestamp with time zone,
    sync_status public.devonthinksyncstatus NOT NULL DEFAULT 'PENDING',
    error_message text,
    scientific_paper_id integer,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- DEVONthink folders (depends on user)
CREATE TABLE public.devonthink_folders (
    dt_uuid character varying(255) NOT NULL,
    dt_path text NOT NULL,
    folder_name character varying NOT NULL,
    parent_dt_uuid character varying(255),
    depth_level integer NOT NULL DEFAULT 0,
    sync_status public.devonthinksyncstatus NOT NULL DEFAULT 'PENDING',
    last_sync_date timestamp with time zone,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Paper annotations (depends on scientific_papers and user)
CREATE TABLE public.paper_annotations (
    content text NOT NULL,
    annotation_type character varying NOT NULL DEFAULT 'note',
    page_number integer,
    x_coordinate double precision,
    y_coordinate double precision,
    width double precision,
    height double precision,
    color character varying,
    is_private boolean NOT NULL DEFAULT true,
    paper_id integer NOT NULL,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);

-- Paper tags many-to-many table (depends on scientific_papers and tags)
CREATE TABLE public.paper_tags (
    paper_id integer NOT NULL,
    tag_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- ========================================
-- 4. CREATE SEQUENCES
-- ========================================

CREATE SEQUENCE public.chats_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.chats_id_seq OWNED BY public.chats.id;

CREATE SEQUENCE public.chunks_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.chunks_id_seq OWNED BY public.chunks.id;

CREATE SEQUENCE public.devonthink_folders_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.devonthink_folders_id_seq OWNED BY public.devonthink_folders.id;

CREATE SEQUENCE public.devonthink_sync_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.devonthink_sync_id_seq OWNED BY public.devonthink_sync.id;

CREATE SEQUENCE public.documents_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;

CREATE SEQUENCE public.paper_annotations_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.paper_annotations_id_seq OWNED BY public.paper_annotations.id;

CREATE SEQUENCE public.podcasts_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.podcasts_id_seq OWNED BY public.podcasts.id;

CREATE SEQUENCE public.scientific_papers_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.scientific_papers_id_seq OWNED BY public.scientific_papers.id;

CREATE SEQUENCE public.search_source_connectors_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.search_source_connectors_id_seq OWNED BY public.search_source_connectors.id;

CREATE SEQUENCE public.searchspaces_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.searchspaces_id_seq OWNED BY public.searchspaces.id;

CREATE SEQUENCE public.tags_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
ALTER SEQUENCE public.tags_id_seq OWNED BY public.tags.id;

-- ========================================
-- 5. SET DEFAULT VALUES
-- ========================================

ALTER TABLE ONLY public.chats ALTER COLUMN id SET DEFAULT nextval('public.chats_id_seq'::regclass);
ALTER TABLE ONLY public.chunks ALTER COLUMN id SET DEFAULT nextval('public.chunks_id_seq'::regclass);
ALTER TABLE ONLY public.devonthink_folders ALTER COLUMN id SET DEFAULT nextval('public.devonthink_folders_id_seq'::regclass);
ALTER TABLE ONLY public.devonthink_sync ALTER COLUMN id SET DEFAULT nextval('public.devonthink_sync_id_seq'::regclass);
ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);
ALTER TABLE ONLY public.paper_annotations ALTER COLUMN id SET DEFAULT nextval('public.paper_annotations_id_seq'::regclass);
ALTER TABLE ONLY public.podcasts ALTER COLUMN id SET DEFAULT nextval('public.podcasts_id_seq'::regclass);
ALTER TABLE ONLY public.scientific_papers ALTER COLUMN id SET DEFAULT nextval('public.scientific_papers_id_seq'::regclass);
ALTER TABLE ONLY public.search_source_connectors ALTER COLUMN id SET DEFAULT nextval('public.search_source_connectors_id_seq'::regclass);
ALTER TABLE ONLY public.searchspaces ALTER COLUMN id SET DEFAULT nextval('public.searchspaces_id_seq'::regclass);
ALTER TABLE ONLY public.tags ALTER COLUMN id SET DEFAULT nextval('public.tags_id_seq'::regclass);

-- ========================================
-- 6. CREATE PRIMARY KEY CONSTRAINTS
-- ========================================

ALTER TABLE ONLY public.chats ADD CONSTRAINT chats_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.chunks ADD CONSTRAINT chunks_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.devonthink_folders ADD CONSTRAINT devonthink_folders_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.devonthink_sync ADD CONSTRAINT devonthink_sync_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.documents ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.paper_annotations ADD CONSTRAINT paper_annotations_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.paper_tags ADD CONSTRAINT paper_tags_pkey PRIMARY KEY (paper_id, tag_id);
ALTER TABLE ONLY public.podcasts ADD CONSTRAINT podcasts_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.scientific_papers ADD CONSTRAINT scientific_papers_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.search_source_connectors ADD CONSTRAINT search_source_connectors_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.searchspaces ADD CONSTRAINT searchspaces_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.tags ADD CONSTRAINT tags_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public."user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);

-- ========================================
-- 7. CREATE UNIQUE CONSTRAINTS
-- ========================================

ALTER TABLE ONLY public.scientific_papers ADD CONSTRAINT scientific_papers_doi_key UNIQUE (doi);
ALTER TABLE ONLY public.scientific_papers ADD CONSTRAINT scientific_papers_pmid_key UNIQUE (pmid);
ALTER TABLE ONLY public.scientific_papers ADD CONSTRAINT scientific_papers_arxiv_id_key UNIQUE (arxiv_id);
ALTER TABLE ONLY public.devonthink_sync ADD CONSTRAINT devonthink_sync_dt_uuid_key UNIQUE (dt_uuid);
ALTER TABLE ONLY public.devonthink_sync ADD CONSTRAINT devonthink_sync_local_uuid_key UNIQUE (local_uuid);
ALTER TABLE ONLY public.devonthink_folders ADD CONSTRAINT devonthink_folders_dt_uuid_key UNIQUE (dt_uuid);
ALTER TABLE ONLY public.search_source_connectors ADD CONSTRAINT search_source_connectors_connector_type_key UNIQUE (connector_type);
ALTER TABLE ONLY public."user" ADD CONSTRAINT user_email_key UNIQUE (email);

-- ========================================
-- 8. CREATE INDEXES
-- ========================================

-- Vector indexes for semantic search
CREATE INDEX chucks_vector_index ON public.chunks USING hnsw (embedding public.vector_cosine_ops);
CREATE INDEX document_vector_index ON public.documents USING hnsw (embedding public.vector_cosine_ops);

-- Full-text search indexes
CREATE INDEX chucks_search_index ON public.chunks USING gin (to_tsvector('english'::regconfig, content));
CREATE INDEX document_search_index ON public.documents USING gin (to_tsvector('english'::regconfig, content));

-- Standard B-tree indexes for performance
CREATE INDEX ix_chats_created_at ON public.chats USING btree (created_at);
CREATE INDEX ix_chats_id ON public.chats USING btree (id);
CREATE INDEX ix_chats_title ON public.chats USING btree (title);

CREATE INDEX ix_chunks_created_at ON public.chunks USING btree (created_at);
CREATE INDEX ix_chunks_id ON public.chunks USING btree (id);

CREATE INDEX ix_devonthink_folders_created_at ON public.devonthink_folders USING btree (created_at);
CREATE INDEX ix_devonthink_folders_dt_path ON public.devonthink_folders USING btree (dt_path);
CREATE INDEX ix_devonthink_folders_dt_uuid ON public.devonthink_folders USING btree (dt_uuid);
CREATE INDEX ix_devonthink_folders_id ON public.devonthink_folders USING btree (id);
CREATE INDEX ix_devonthink_folders_parent_dt_uuid ON public.devonthink_folders USING btree (parent_dt_uuid);

CREATE INDEX ix_devonthink_sync_created_at ON public.devonthink_sync USING btree (created_at);
CREATE INDEX ix_devonthink_sync_dt_uuid ON public.devonthink_sync USING btree (dt_uuid);
CREATE INDEX ix_devonthink_sync_id ON public.devonthink_sync USING btree (id);
CREATE INDEX ix_devonthink_sync_local_uuid ON public.devonthink_sync USING btree (local_uuid);

CREATE INDEX ix_documents_created_at ON public.documents USING btree (created_at);
CREATE INDEX ix_documents_id ON public.documents USING btree (id);
CREATE INDEX ix_documents_title ON public.documents USING btree (title);

CREATE INDEX ix_paper_annotations_created_at ON public.paper_annotations USING btree (created_at);
CREATE INDEX ix_paper_annotations_id ON public.paper_annotations USING btree (id);

CREATE INDEX ix_podcasts_created_at ON public.podcasts USING btree (created_at);
CREATE INDEX ix_podcasts_id ON public.podcasts USING btree (id);
CREATE INDEX ix_podcasts_title ON public.podcasts USING btree (title);

CREATE INDEX ix_scientific_papers_arxiv_id ON public.scientific_papers USING btree (arxiv_id);
CREATE INDEX ix_scientific_papers_created_at ON public.scientific_papers USING btree (created_at);
CREATE INDEX ix_scientific_papers_doi ON public.scientific_papers USING btree (doi);
CREATE INDEX ix_scientific_papers_dt_source_uuid ON public.scientific_papers USING btree (dt_source_uuid);
CREATE INDEX ix_scientific_papers_file_hash ON public.scientific_papers USING btree (file_hash);
CREATE INDEX ix_scientific_papers_id ON public.scientific_papers USING btree (id);
CREATE INDEX ix_scientific_papers_journal ON public.scientific_papers USING btree (journal);
CREATE INDEX ix_scientific_papers_pmid ON public.scientific_papers USING btree (pmid);
CREATE INDEX ix_scientific_papers_publication_date ON public.scientific_papers USING btree (publication_date);
CREATE INDEX ix_scientific_papers_publication_year ON public.scientific_papers USING btree (publication_year);
CREATE INDEX ix_scientific_papers_title ON public.scientific_papers USING btree (title);

CREATE INDEX ix_search_source_connectors_created_at ON public.search_source_connectors USING btree (created_at);
CREATE INDEX ix_search_source_connectors_id ON public.search_source_connectors USING btree (id);
CREATE INDEX ix_search_source_connectors_name ON public.search_source_connectors USING btree (name);

CREATE INDEX ix_searchspaces_created_at ON public.searchspaces USING btree (created_at);
CREATE INDEX ix_searchspaces_id ON public.searchspaces USING btree (id);
CREATE INDEX ix_searchspaces_name ON public.searchspaces USING btree (name);

CREATE INDEX ix_tags_created_at ON public.tags USING btree (created_at);
CREATE INDEX ix_tags_id ON public.tags USING btree (id);
CREATE INDEX ix_tags_name ON public.tags USING btree (name);
CREATE INDEX ix_tags_parent_id ON public.tags USING btree (parent_id);
CREATE INDEX ix_tags_user_id ON public.tags USING btree (user_id);

CREATE INDEX ix_user_email ON public."user" USING btree (email);

-- ========================================
-- 9. CREATE FOREIGN KEY CONSTRAINTS
-- ========================================

ALTER TABLE ONLY public.chats ADD CONSTRAINT chats_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.chunks ADD CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.devonthink_folders ADD CONSTRAINT devonthink_folders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.devonthink_sync ADD CONSTRAINT devonthink_sync_scientific_paper_id_fkey FOREIGN KEY (scientific_paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.devonthink_sync ADD CONSTRAINT devonthink_sync_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.documents ADD CONSTRAINT documents_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.paper_annotations ADD CONSTRAINT paper_annotations_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.paper_annotations ADD CONSTRAINT paper_annotations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.paper_tags ADD CONSTRAINT paper_tags_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.paper_tags ADD CONSTRAINT paper_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tags(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.podcasts ADD CONSTRAINT podcasts_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.scientific_papers ADD CONSTRAINT scientific_papers_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.search_source_connectors ADD CONSTRAINT search_source_connectors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.searchspaces ADD CONSTRAINT searchspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.tags ADD CONSTRAINT tags_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.tags(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.tags ADD CONSTRAINT tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;

-- ========================================
-- SCHEMA CREATION COMPLETE
-- ========================================

-- To use this script:
-- 1. Create a new PostgreSQL database: CREATE DATABASE bibliography_db;
-- 2. Connect to the database: \c bibliography_db
-- 3. Run this script: \i create_bibliography_db.sql
--
-- The schema includes:
-- - pgvector extension for vector embeddings
-- - All tables with proper relationships and constraints
-- - Indexes for performance (including vector and full-text search)
-- - Sequences for auto-incrementing IDs
-- - Foreign key constraints with CASCADE deletes where appropriate