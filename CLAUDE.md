# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bibliography is a comprehensive bibliography management system for scientific papers with PDF processing, metadata extraction, citation formatting, and team collaboration features. The system uses FastAPI for the backend and Streamlit for the frontend, with PostgreSQL + pgvector for semantic search capabilities.

## Architecture

- **Backend**: FastAPI application in `/backend/` with Python 3.12+
- **Frontend**: Streamlit web interface in `/frontend/`
- **Database**: PostgreSQL with pgvector extension for semantic search
- **Storage**: UUID-based file storage for PDFs (not database BLOBs)

Key directories:
- `backend/app/db.py` - Database models and connection
- `backend/app/services/` - Business logic (PDF processing, citations, annotations, etc.)
- `backend/app/routes/` - API endpoints 
- `backend/app/schemas/` - Pydantic models
- `frontend/app.py` - Main Streamlit application

## Development Commands

### Backend Setup
```bash
cd backend
pip install -e .
```

### Frontend Setup  
```bash
cd frontend
pip install -r requirements.txt
```

### Running the Application
```bash
# Backend (FastAPI)
cd backend
python main.py --reload
# API available at http://localhost:8000, docs at http://localhost:8000/docs

# Frontend (Streamlit)  
cd frontend
streamlit run app.py
# Web interface at http://localhost:8501
```

### Database Setup
Requires PostgreSQL with pgvector extension. Create `.env` file in backend directory with:
```
DATABASE_URL=postgresql+asyncpg://username:password@localhost/bibliography_db
SECRET_KEY=your-secret-key-here
AUTH_TYPE=basic
EMBEDDING_MODEL=openai://nomic-embed-text
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
PDF_STORAGE_ROOT=./data/pdfs
WATCHED_FOLDER=./data/watched
```

## Core Services

### PDF Processing (`app/services/pdf_processor.py`)
Handles PDF text extraction and metadata parsing using PyMuPDF.

### File Storage (`app/services/file_storage.py`) 
UUID-based file management with deduplication via SHA256 hashes. Files stored in `data/pdfs/YYYY/MM/` structure.

### Citation Formatting (`app/services/citation_formatter.py`)
Generates citations in multiple formats (APA, MLA, Chicago, IEEE, Harvard, BibTeX).

### Annotations (`app/services/annotation_service.py`)
User-attributed annotations with privacy controls for team collaboration.

### Semantic Search (`app/services/semantic_search_service.py`)
AI-powered search using pgvector for similarity scoring and insights.

### Folder Watcher (`app/services/folder_watcher.py`)
Automatic processing of PDFs dropped into watched folders.

## Database Models

Key models in `app/db.py`:
- **ScientificPaper**: Core paper metadata (title, authors, DOI, etc.)
- **Document**: Full-text content and embeddings for search  
- **PaperAnnotation**: User annotations with privacy controls
- **User**: Authentication and user management
- **SearchSpace**: Organization and access control
- **Chat**: Research conversation history

## Authentication

Uses fastapi-users for authentication. Supports basic auth by default, configurable for Google OAuth via `AUTH_TYPE` environment variable.

## API Structure

All API routes are in `/api/v1/` namespace:
- `/papers/` - Paper management (upload, search, citation, download)
- `/annotations/` - Annotation CRUD with privacy controls
- `/semantic-search/` - Enhanced AI search capabilities
- `/dashboard/` - Analytics and overview data
- `/auth/` - User authentication endpoints

## File Storage Strategy

PDFs are stored as files (not database BLOBs) using UUID-based naming:
- Better database performance
- Easier backups and file management
- Automatic deduplication via SHA256 hashes
- Efficient file serving

## DEVONthink Integration

This system supports two methods for importing papers from DEVONthink:

### Method 1: CSV Export (Recommended)

**Simple, reliable workflow using DEVONthink Smart Rules:**

1. **DEVONthink Smart Rule** exports selected records to:
   - CSV file: `~/PDFs/Evidence_Library_Sync/active_library.csv`
   - PDF files: `~/PDFs/Evidence_Library_Sync/{uuid}.pdf`

2. **Import Script** processes the CSV and PDFs:
   ```bash
   python backend/scripts/import_from_devonthink_csv.py \
     --csv ~/PDFs/Evidence_Library_Sync/active_library.csv \
     --user-id YOUR_USER_ID
   ```

3. **Full Pipeline**: Automatically handles:
   - PDF storage with UUID naming
   - Metadata extraction from PDFs
   - Thumbnail generation
   - Vectorization for semantic search
   - Duplicate detection (by DEVONthink UUID)

**See**: `DEVONTHINK_CSV_WORKFLOW.md` for complete instructions

**Advantages**:
- Simple setup (just a Smart Rule)
- Full control over which records to export
- No additional servers required
- Reliable and easy to troubleshoot

### Method 2: MCP Server Integration (Advanced)

**Full database sync with folder hierarchy preservation:**

- **Automated PDF Ingestion**: Syncs PDFs from DEVONthink database via MCP server
- **Hierarchy Preservation**: Maintains your DEVONthink folder structure
- **Metadata Extraction**: Preserves custom fields and tags from DEVONthink
- **Incremental Sync**: Monitors for changes and syncs only new/modified files

**API Endpoints**:
- `POST /api/v1/devonthink/sync` - Full database sync
- `POST /api/v1/devonthink/sync/incremental` - Sync recent changes only
- `GET /api/v1/devonthink/sync/status` - Check sync status of records
- `GET /api/v1/devonthink/folders` - View preserved folder hierarchy

**Setup Requirements**:
1. Install DEVONthink MCP server: `npx -y mcp-server-devonthink`
2. Configure database name (default: "Reference")
3. Run sync via API endpoints

**Database Models**:
- **DevonthinkSync**: Tracks sync status between DEVONthink and local system
- **DevonthinkFolder**: Preserves DEVONthink folder hierarchy
- **ScientificPaper**: Extended with `dt_source_uuid` and `dt_source_path` fields

**Advantages**:
- Preserves folder hierarchy
- Automatic monitoring for changes
- Full database sync capability

## Environment Variables

Required for backend operation:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `AUTH_TYPE` - Authentication type (basic/google)
- `EMBEDDING_MODEL` - Model for semantic search
- `PDF_STORAGE_ROOT` - PDF file storage directory
- `WATCHED_FOLDER` - Auto-processing folder path

## Thumbnail Generation & PDF Viewing

**✅ FULLY IMPLEMENTED - January 2025**

The system now includes complete support for PDF thumbnails and viewing:

### Backend Features
- **Thumbnail Generator Service** (`app/services/thumbnail_generator.py`)
  - Generates 300x400px thumbnails from PDF first pages
  - UUID-based storage matching PDF structure
  - Automatic caching with on-demand generation
  - Batch processing support

- **API Endpoints** (`app/routes/papers_routes.py`)
  - `GET /api/v1/papers/{paper_id}/thumbnail` - Serve thumbnail
  - `GET /api/v1/papers/{paper_id}/pdf` - Serve PDF for viewing
  - `POST /api/v1/papers/thumbnails/generate-batch` - Batch generation

### Frontend Features
- **BookCard Component**: Displays thumbnails with graceful fallback
- **PDFViewer Component**: Real PDF viewing in iframe with zoom controls
- **Automatic Generation**: Thumbnails created on first view and cached

### File Structure
```
data/
├── pdfs/           # UUID-based PDF storage
│   └── YYYY/MM/{uuid}.pdf
└── thumbnails/     # Thumbnail storage
    └── YYYY/MM/{paper_id}.jpg
```

**See**: `THUMBNAIL_PDF_SETUP.md` and `QUICKSTART_THUMBNAILS.md` for details

## Current Status (Sept 20, 2025)

**✅ DEVONthink Sync Pipeline - FULLY OPERATIONAL**

The DEVONthink integration has been fully implemented, tested, and verified working end-to-end:

### Infrastructure Ready
- Database `bibliography_db` created with pgvector extension
- Virtual environment configured with all dependencies resolved
- FastAPI server running successfully on http://localhost:8000
- All database tables created and models loaded

### DEVONthink API Endpoints Working
All endpoints are registered and accessible at `/devonthink/*`:
- `/health` - Health check (tested ✅)
- `/sync` - Full sync operation (tested ✅ - 100 records with 0 errors)
- `/sync/status` - Get sync status
- `/sync/incremental` - Incremental sync
- `/folders` - Folder hierarchy mapping
- `/monitor` - Change monitoring
- `/stats` - Sync statistics
- `/sync/{dt_uuid}` - Delete sync record

### Architecture Complete & Verified
The 5-step sync workflow is implemented and working in `DevonthinkSyncService`:
1. **Map directories** → Preserves hierarchical structure ✅
2. **Fetch metadata + assign UUID** → Tracks DEVONthink → local mapping ✅
3. **Copy PDF binaries** → UUID-based file storage ✅
4. **Retrieve for vectorization** → Integration with existing pipeline ✅
5. **Monitor changes** → Continuous sync capability ✅

### Critical Fixes Applied (Sept 20, 2025)
Two major technical issues were resolved to achieve full functionality:

**1. SQLAlchemy Async Context Issue (semantic_search_service.py:218-246)**
- **Problem**: `greenlet_spawn has not been called; can't call await_only() here` errors during vectorization
- **Root Cause**: Using `loop.run_in_executor()` for embedding generation created thread context conflicts with SQLAlchemy async operations
- **Solution**: Removed thread executors and used synchronous embedding generation with `config.embedding_model_instance.embed_query()`
- **Files Modified**: `app/services/semantic_search_service.py`

**2. PDF Document Lifecycle Bug (pdf_processor.py:73-97)**
- **Problem**: "document closed" errors during PDF processing
- **Root Cause**: Accessing `len(doc)` after calling `doc.close()` in the return statement
- **Solution**: Captured `page_count = len(doc)` before closing document
- **Files Modified**: `app/services/pdf_processor.py`

### Production Ready
- **Tested**: 100-record sync completed successfully with 0 errors
- **Vectorization**: Full semantic search embeddings working properly
- **MCP Integration**: Real DEVONthink MCP server connection functional
- **File Processing**: PDF copying, metadata extraction, and database storage working
- **Ready for**: Full 2000+ record migration when needed

### Next Steps
- Run full migration of 2000+ records from DEVONthink "Reference" database
- Set up authentication flow for production use
- Enable continuous monitoring for file changes