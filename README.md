# Bibliography Manager

A comprehensive bibliography management system for scientific papers with PDF processing, metadata extraction, citation formatting, and team collaboration features.

## Features ✨

### Core Functionality
- 📄 **PDF Processing**: Automatic text extraction and metadata parsing from scientific papers
- 🔍 **Smart Search**: Full-text and semantic search capabilities using pgvector
- 🧠 **Semantic Search**: Advanced AI-powered search with similarity scoring and insights
- 📊 **Analytics Dashboard**: Comprehensive analytics and database overview
- 📚 **Citation Management**: Generate citations in multiple formats (APA, MLA, Chicago, IEEE, Harvard, BibTeX)
- 📝 **Team Annotations**: User-attributed annotations with privacy controls for team collaboration
- 📁 **Folder Watching**: Automatic processing of PDFs dropped into watched folders
- 🔐 **User Authentication**: Secure user registration and login system

### Technical Features
- **UUID-based File Storage**: Efficient file management with deduplication
- **Scientific Paper Schema**: Specialized database schema for academic papers
- **RESTful API**: Complete FastAPI backend with comprehensive endpoints
- **Streamlit Frontend**: User-friendly web interface
- **PostgreSQL + pgvector**: Advanced vector search capabilities

## Architecture 🏗️

```
bibliography/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── db.py           # Database models and connection
│   │   ├── services/       # Business logic services
│   │   │   ├── pdf_processor.py        # PDF processing
│   │   │   ├── file_storage.py         # File management
│   │   │   ├── folder_watcher.py       # Automatic processing
│   │   │   ├── citation_formatter.py   # Citation generation
│   │   │   ├── annotation_service.py   # Team annotations
│   │   │   └── paper_manager.py        # Comprehensive paper management
│   │   ├── routes/         # API endpoints
│   │   └── schemas/        # Pydantic models
│   └── main.py             # Application entry point
└── frontend/               # Streamlit web interface
    ├── app.py              # Main Streamlit app
    └── requirements.txt    # Frontend dependencies
```

## Quick Start 🚀

### Prerequisites
- Python 3.12+
- PostgreSQL with pgvector extension
- PDF files to manage

### 1. Environment Setup

```bash
# Clone or navigate to the project
cd /Users/drjforrest/dev/devprojects/bibliography

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install backend dependencies
cd backend
pip install -e .

# Install frontend dependencies
cd ../frontend
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Install PostgreSQL and pgvector
# On macOS with Homebrew:
brew install postgresql pgvector

# Start PostgreSQL
brew services start postgresql

# Create database
createdb bibliography_db

# Create .env file in backend directory
cd ../backend
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://username:password@localhost/bibliography_db
SECRET_KEY=your-secret-key-here
AUTH_TYPE=basic
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKERS_MODEL_NAME=flashrank
RERANKERS_MODEL_TYPE=flashrank
FAST_LLM=gpt-3.5-turbo
LONG_CONTEXT_LLM=gpt-4
STRATEGIC_LLM=gpt-4
PDF_STORAGE_ROOT=./data/pdfs
WATCHED_FOLDER=./data/watched
EOF
```

### 3. Running the Application

#### Backend (FastAPI)
```bash
cd backend
python main.py --reload
# API will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

#### Frontend (Streamlit)
```bash
cd frontend
streamlit run app.py
# Web interface available at http://localhost:8501
```

## Usage Guide 📖

### 1. First Time Setup
1. Register a user account via API or create one in the database
2. Create a search space for organizing your papers
3. Start the folder watcher for automatic processing (optional)

### 2. Adding Papers

#### Via Web Interface
1. Go to the "Upload" tab
2. Select your search space
3. Upload PDF files
4. View extracted metadata and processing results

#### Via Watched Folder
1. Start the folder watcher via API: `POST /api/v1/papers/watcher/start`
2. Drop PDF files into the watched folder
3. Papers will be automatically processed

#### Via API
```bash
curl -X POST "http://localhost:8000/api/v1/papers/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@paper.pdf" \
  -F "search_space_id=1"
```

### 3. Team Collaboration

#### Adding Annotations
```bash
curl -X POST "http://localhost:8000/api/v1/annotations/?paper_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is an important finding",
    "annotation_type": "note",
    "page_number": 5,
    "is_private": false
  }'
```

#### Privacy Controls
- **Private annotations**: Only visible to the creator
- **Public annotations**: Visible to all team members
- Toggle privacy: `POST /api/v1/annotations/{id}/toggle-privacy`

### 4. Citation Generation

#### Via Web Interface
1. Browse to a paper
2. Click "Get Citation"
3. Select citation style (APA, MLA, Chicago, etc.)
4. Copy the formatted citation

#### Via API
```bash
curl -X POST "http://localhost:8000/api/v1/papers/1/citation" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"style": "apa"}'
```

## File Storage Strategy 📁

The system uses **UUID-based file storage** instead of storing PDFs as database BLOBs:

### Storage Structure
```
data/
├── pdfs/
│   ├── 2025/
│   │   └── 01/
│   │       ├── uuid1.pdf
│   │       └── uuid2.pdf
└── watched/          # Drop PDFs here for auto-processing
    └── new-paper.pdf
```

### Benefits
- ✅ Better database performance
- ✅ Easier backups and file management
- ✅ Efficient file serving
- ✅ Automatic deduplication via SHA256 hashes

## API Endpoints 🛠️

### Papers
- `GET /api/v1/papers/` - List papers
- `POST /api/v1/papers/upload` - Upload PDF
- `POST /api/v1/papers/search` - Search papers
- `GET /api/v1/papers/{id}` - Get paper details
- `POST /api/v1/papers/{id}/citation` - Get citation
- `GET /api/v1/papers/{id}/download` - Download PDF
- `DELETE /api/v1/papers/{id}` - Delete paper

### Annotations
- `POST /api/v1/annotations/?paper_id={id}` - Create annotation
- `GET /api/v1/annotations/paper/{paper_id}` - Get paper annotations
- `GET /api/v1/annotations/user/me` - Get user's annotations
- `PUT /api/v1/annotations/{id}` - Update annotation
- `DELETE /api/v1/annotations/{id}` - Delete annotation
- `POST /api/v1/annotations/{id}/toggle-privacy` - Toggle privacy

### Folder Watcher
- `POST /api/v1/papers/watcher/start` - Start watching
- `POST /api/v1/papers/watcher/stop` - Stop watching
- `GET /api/v1/papers/watcher/status` - Get status

### Semantic Search
- `POST /api/v1/semantic-search/` - Enhanced semantic search
- `GET /api/v1/semantic-search/similar/{paper_id}` - Find similar papers
- `GET /api/v1/semantic-search/suggestions` - Get search suggestions
- `GET /api/v1/semantic-search/quick/{query}` - Quick search

### Dashboard & Analytics
- `GET /api/v1/dashboard/user` - User dashboard
- `GET /api/v1/dashboard/global` - Global dashboard (admin)
- `GET /api/v1/dashboard/overview` - Quick overview
- `GET /api/v1/dashboard/activity` - Recent activity
- `GET /api/v1/dashboard/analytics` - Paper analytics

## Database Schema 🗄️

### Key Models
- **ScientificPaper**: Core paper metadata (title, authors, DOI, etc.)
- **Document**: Full-text content and embeddings for search
- **PaperAnnotation**: User-attributed annotations with privacy controls
- **User**: Authentication and user management
- **SearchSpace**: Organization and access control

### Team Collaboration Features
- User-attributed annotations
- Privacy controls (private/public annotations)
- Search across team annotations
- Statistics and reporting

## Development 👨‍💻

### Adding New Citation Styles
1. Edit `app/services/citation_formatter.py`
2. Add new formatting method
3. Update `get_available_styles()` method

### Extending PDF Processing
1. Modify `app/services/pdf_processor.py`
2. Add new extraction methods
3. Update the database schema if needed

### Custom Annotation Types
1. Update annotation type validation in schemas
2. Add frontend support for new types
3. Consider PDF rendering requirements

## Troubleshooting 🔧

### Common Issues

#### PDF Processing Fails
- Check file permissions and storage paths
- Verify PyMuPDF installation
- Check PDF file integrity

#### Database Connection Issues
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure pgvector extension is installed

#### Missing Dependencies
```bash
# Install system dependencies (macOS)
brew install postgresql pgvector

# Install Python dependencies
pip install -e .
```

#### Folder Watcher Not Working
- Check folder permissions
- Verify WATCHED_FOLDER path in config
- Check service logs for errors

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

This project is licensed under the MIT License.

## Acknowledgments 🙏

- FastAPI for the excellent web framework
- Streamlit for the rapid frontend development
- PyMuPDF for PDF processing capabilities
- pgvector for semantic search functionality