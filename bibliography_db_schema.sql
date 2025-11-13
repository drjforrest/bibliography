--
-- PostgreSQL database dump
--

\restrict 6O49cUjhWO4YdBy7SHe2SDfYdNw5ttSWTxtkOAVbeyhEaKmaPyb4ushbXZlz4zZ

-- Dumped from database version 17.6 (Homebrew)
-- Dumped by pg_dump version 17.6 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: chattype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.chattype AS ENUM (
    'GENERAL',
    'DEEP',
    'DEEPER',
    'DEEPEST'
);


--
-- Name: devonthinksyncstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.devonthinksyncstatus AS ENUM (
    'PENDING',
    'SYNCED',
    'ERROR',
    'UPDATED'
);


--
-- Name: documenttype; Type: TYPE; Schema: public; Owner: -
--

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


--
-- Name: searchsourceconnectortype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.searchsourceconnectortype AS ENUM (
    'SERPER_API',
    'TAVILY_API',
    'LINKUP_API',
    'SLACK_CONNECTOR',
    'NOTION_CONNECTOR',
    'GITHUB_CONNECTOR',
    'LINEAR_CONNECTOR'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: chats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chats (
    type public.chattype NOT NULL,
    title character varying NOT NULL,
    initial_connectors character varying[],
    messages json NOT NULL,
    search_space_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: chats_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chats_id_seq OWNED BY public.chats.id;


--
-- Name: chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chunks (
    content text NOT NULL,
    embedding public.vector(384),
    document_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chunks_id_seq OWNED BY public.chunks.id;


--
-- Name: devonthink_folders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devonthink_folders (
    dt_uuid character varying(255) NOT NULL,
    dt_path text NOT NULL,
    folder_name character varying NOT NULL,
    parent_dt_uuid character varying(255),
    depth_level integer NOT NULL,
    sync_status public.devonthinksyncstatus NOT NULL,
    last_sync_date timestamp with time zone,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: devonthink_folders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.devonthink_folders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: devonthink_folders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.devonthink_folders_id_seq OWNED BY public.devonthink_folders.id;


--
-- Name: devonthink_sync; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devonthink_sync (
    dt_uuid character varying(255) NOT NULL,
    dt_path text,
    dt_modified_date timestamp with time zone,
    local_uuid uuid NOT NULL,
    last_sync_date timestamp with time zone,
    sync_status public.devonthinksyncstatus NOT NULL,
    error_message text,
    scientific_paper_id integer,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: devonthink_sync_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.devonthink_sync_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: devonthink_sync_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.devonthink_sync_id_seq OWNED BY public.devonthink_sync.id;


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- Name: paper_annotations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_annotations (
    content text NOT NULL,
    annotation_type character varying NOT NULL,
    page_number integer,
    x_coordinate double precision,
    y_coordinate double precision,
    width double precision,
    height double precision,
    color character varying,
    is_private boolean NOT NULL,
    paper_id integer NOT NULL,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: paper_annotations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.paper_annotations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: paper_annotations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.paper_annotations_id_seq OWNED BY public.paper_annotations.id;


--
-- Name: paper_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_tags (
    paper_id integer NOT NULL,
    tag_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: podcasts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.podcasts (
    title character varying NOT NULL,
    podcast_transcript json NOT NULL,
    file_location character varying(500) NOT NULL,
    search_space_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: podcasts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.podcasts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: podcasts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.podcasts_id_seq OWNED BY public.podcasts.id;


--
-- Name: scientific_papers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scientific_papers (
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
    keywords character varying[],
    full_text text,
    file_path character varying NOT NULL,
    file_size integer,
    file_hash character varying,
    citation_count integer,
    "references" json,
    cited_by json,
    subject_areas character varying[],
    tags character varying[],
    confidence_score double precision,
    is_open_access boolean,
    processing_status character varying NOT NULL,
    extraction_metadata json,
    dt_source_uuid character varying(255),
    dt_source_path text,
    document_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    lay_summary text
);


--
-- Name: scientific_papers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scientific_papers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scientific_papers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scientific_papers_id_seq OWNED BY public.scientific_papers.id;


--
-- Name: search_source_connectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.search_source_connectors (
    name character varying(100) NOT NULL,
    connector_type public.searchsourceconnectortype NOT NULL,
    is_indexable boolean NOT NULL,
    last_indexed_at timestamp with time zone,
    config json NOT NULL,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: search_source_connectors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.search_source_connectors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: search_source_connectors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.search_source_connectors_id_seq OWNED BY public.search_source_connectors.id;


--
-- Name: searchspaces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.searchspaces (
    name character varying(100) NOT NULL,
    description character varying(500),
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: searchspaces_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.searchspaces_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: searchspaces_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.searchspaces_id_seq OWNED BY public.searchspaces.id;


--
-- Name: tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tags (
    name character varying(100) NOT NULL,
    description text,
    color character varying(20),
    icon character varying(50),
    parent_id integer,
    user_id uuid NOT NULL,
    id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: tags_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tags_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tags_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tags_id_seq OWNED BY public.tags.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    hashed_password character varying(1024) NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    is_verified boolean NOT NULL
);


--
-- Name: chats id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chats ALTER COLUMN id SET DEFAULT nextval('public.chats_id_seq'::regclass);


--
-- Name: chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks ALTER COLUMN id SET DEFAULT nextval('public.chunks_id_seq'::regclass);


--
-- Name: devonthink_folders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_folders ALTER COLUMN id SET DEFAULT nextval('public.devonthink_folders_id_seq'::regclass);


--
-- Name: devonthink_sync id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_sync ALTER COLUMN id SET DEFAULT nextval('public.devonthink_sync_id_seq'::regclass);


--
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- Name: paper_annotations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_annotations ALTER COLUMN id SET DEFAULT nextval('public.paper_annotations_id_seq'::regclass);


--
-- Name: podcasts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.podcasts ALTER COLUMN id SET DEFAULT nextval('public.podcasts_id_seq'::regclass);


--
-- Name: scientific_papers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scientific_papers ALTER COLUMN id SET DEFAULT nextval('public.scientific_papers_id_seq'::regclass);


--
-- Name: search_source_connectors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_source_connectors ALTER COLUMN id SET DEFAULT nextval('public.search_source_connectors_id_seq'::regclass);


--
-- Name: searchspaces id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.searchspaces ALTER COLUMN id SET DEFAULT nextval('public.searchspaces_id_seq'::regclass);


--
-- Name: tags id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags ALTER COLUMN id SET DEFAULT nextval('public.tags_id_seq'::regclass);


--
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- Name: chunks chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_pkey PRIMARY KEY (id);


--
-- Name: devonthink_folders devonthink_folders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_folders
    ADD CONSTRAINT devonthink_folders_pkey PRIMARY KEY (id);


--
-- Name: devonthink_sync devonthink_sync_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_sync
    ADD CONSTRAINT devonthink_sync_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: paper_annotations paper_annotations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_annotations
    ADD CONSTRAINT paper_annotations_pkey PRIMARY KEY (id);


--
-- Name: paper_tags paper_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_tags
    ADD CONSTRAINT paper_tags_pkey PRIMARY KEY (paper_id, tag_id);


--
-- Name: podcasts podcasts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.podcasts
    ADD CONSTRAINT podcasts_pkey PRIMARY KEY (id);


--
-- Name: scientific_papers scientific_papers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scientific_papers
    ADD CONSTRAINT scientific_papers_pkey PRIMARY KEY (id);


--
-- Name: search_source_connectors search_source_connectors_connector_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_source_connectors
    ADD CONSTRAINT search_source_connectors_connector_type_key UNIQUE (connector_type);


--
-- Name: search_source_connectors search_source_connectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_source_connectors
    ADD CONSTRAINT search_source_connectors_pkey PRIMARY KEY (id);


--
-- Name: searchspaces searchspaces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.searchspaces
    ADD CONSTRAINT searchspaces_pkey PRIMARY KEY (id);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: chucks_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chucks_search_index ON public.chunks USING gin (to_tsvector('english'::regconfig, content));


--
-- Name: chucks_vector_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX chucks_vector_index ON public.chunks USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: document_search_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX document_search_index ON public.documents USING gin (to_tsvector('english'::regconfig, content));


--
-- Name: document_vector_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX document_vector_index ON public.documents USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: ix_chats_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chats_created_at ON public.chats USING btree (created_at);


--
-- Name: ix_chats_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chats_id ON public.chats USING btree (id);


--
-- Name: ix_chats_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chats_title ON public.chats USING btree (title);


--
-- Name: ix_chunks_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunks_created_at ON public.chunks USING btree (created_at);


--
-- Name: ix_chunks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chunks_id ON public.chunks USING btree (id);


--
-- Name: ix_devonthink_folders_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_folders_created_at ON public.devonthink_folders USING btree (created_at);


--
-- Name: ix_devonthink_folders_dt_path; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_folders_dt_path ON public.devonthink_folders USING btree (dt_path);


--
-- Name: ix_devonthink_folders_dt_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_devonthink_folders_dt_uuid ON public.devonthink_folders USING btree (dt_uuid);


--
-- Name: ix_devonthink_folders_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_folders_id ON public.devonthink_folders USING btree (id);


--
-- Name: ix_devonthink_folders_parent_dt_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_folders_parent_dt_uuid ON public.devonthink_folders USING btree (parent_dt_uuid);


--
-- Name: ix_devonthink_sync_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_sync_created_at ON public.devonthink_sync USING btree (created_at);


--
-- Name: ix_devonthink_sync_dt_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_devonthink_sync_dt_uuid ON public.devonthink_sync USING btree (dt_uuid);


--
-- Name: ix_devonthink_sync_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_devonthink_sync_id ON public.devonthink_sync USING btree (id);


--
-- Name: ix_devonthink_sync_local_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_devonthink_sync_local_uuid ON public.devonthink_sync USING btree (local_uuid);


--
-- Name: ix_documents_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_created_at ON public.documents USING btree (created_at);


--
-- Name: ix_documents_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_id ON public.documents USING btree (id);


--
-- Name: ix_documents_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_title ON public.documents USING btree (title);


--
-- Name: ix_paper_annotations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_annotations_created_at ON public.paper_annotations USING btree (created_at);


--
-- Name: ix_paper_annotations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_paper_annotations_id ON public.paper_annotations USING btree (id);


--
-- Name: ix_podcasts_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_podcasts_created_at ON public.podcasts USING btree (created_at);


--
-- Name: ix_podcasts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_podcasts_id ON public.podcasts USING btree (id);


--
-- Name: ix_podcasts_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_podcasts_title ON public.podcasts USING btree (title);


--
-- Name: ix_scientific_papers_arxiv_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_scientific_papers_arxiv_id ON public.scientific_papers USING btree (arxiv_id);


--
-- Name: ix_scientific_papers_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_created_at ON public.scientific_papers USING btree (created_at);


--
-- Name: ix_scientific_papers_doi; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_scientific_papers_doi ON public.scientific_papers USING btree (doi);


--
-- Name: ix_scientific_papers_dt_source_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_dt_source_uuid ON public.scientific_papers USING btree (dt_source_uuid);


--
-- Name: ix_scientific_papers_file_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_file_hash ON public.scientific_papers USING btree (file_hash);


--
-- Name: ix_scientific_papers_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_id ON public.scientific_papers USING btree (id);


--
-- Name: ix_scientific_papers_journal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_journal ON public.scientific_papers USING btree (journal);


--
-- Name: ix_scientific_papers_pmid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_scientific_papers_pmid ON public.scientific_papers USING btree (pmid);


--
-- Name: ix_scientific_papers_publication_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_publication_date ON public.scientific_papers USING btree (publication_date);


--
-- Name: ix_scientific_papers_publication_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_publication_year ON public.scientific_papers USING btree (publication_year);


--
-- Name: ix_scientific_papers_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scientific_papers_title ON public.scientific_papers USING btree (title);


--
-- Name: ix_search_source_connectors_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_source_connectors_created_at ON public.search_source_connectors USING btree (created_at);


--
-- Name: ix_search_source_connectors_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_source_connectors_id ON public.search_source_connectors USING btree (id);


--
-- Name: ix_search_source_connectors_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_search_source_connectors_name ON public.search_source_connectors USING btree (name);


--
-- Name: ix_searchspaces_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_searchspaces_created_at ON public.searchspaces USING btree (created_at);


--
-- Name: ix_searchspaces_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_searchspaces_id ON public.searchspaces USING btree (id);


--
-- Name: ix_searchspaces_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_searchspaces_name ON public.searchspaces USING btree (name);


--
-- Name: ix_tags_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tags_created_at ON public.tags USING btree (created_at);


--
-- Name: ix_tags_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tags_id ON public.tags USING btree (id);


--
-- Name: ix_tags_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tags_name ON public.tags USING btree (name);


--
-- Name: ix_tags_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tags_parent_id ON public.tags USING btree (parent_id);


--
-- Name: ix_tags_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tags_user_id ON public.tags USING btree (user_id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: chats chats_search_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;


--
-- Name: chunks chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chunks
    ADD CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: devonthink_folders devonthink_folders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_folders
    ADD CONSTRAINT devonthink_folders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: devonthink_sync devonthink_sync_scientific_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_sync
    ADD CONSTRAINT devonthink_sync_scientific_paper_id_fkey FOREIGN KEY (scientific_paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;


--
-- Name: devonthink_sync devonthink_sync_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devonthink_sync
    ADD CONSTRAINT devonthink_sync_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: documents documents_search_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;


--
-- Name: paper_annotations paper_annotations_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_annotations
    ADD CONSTRAINT paper_annotations_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;


--
-- Name: paper_annotations paper_annotations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_annotations
    ADD CONSTRAINT paper_annotations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: paper_tags paper_tags_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_tags
    ADD CONSTRAINT paper_tags_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.scientific_papers(id) ON DELETE CASCADE;


--
-- Name: paper_tags paper_tags_tag_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_tags
    ADD CONSTRAINT paper_tags_tag_id_fkey FOREIGN KEY (tag_id) REFERENCES public.tags(id) ON DELETE CASCADE;


--
-- Name: podcasts podcasts_search_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.podcasts
    ADD CONSTRAINT podcasts_search_space_id_fkey FOREIGN KEY (search_space_id) REFERENCES public.searchspaces(id) ON DELETE CASCADE;


--
-- Name: scientific_papers scientific_papers_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scientific_papers
    ADD CONSTRAINT scientific_papers_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: search_source_connectors search_source_connectors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.search_source_connectors
    ADD CONSTRAINT search_source_connectors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: searchspaces searchspaces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.searchspaces
    ADD CONSTRAINT searchspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: tags tags_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.tags(id) ON DELETE CASCADE;


--
-- Name: tags tags_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 6O49cUjhWO4YdBy7SHe2SDfYdNw5ttSWTxtkOAVbeyhEaKmaPyb4ushbXZlz4zZ

