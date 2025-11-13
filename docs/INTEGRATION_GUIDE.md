# Frontend-Backend Integration Guide

This guide explains how the Next.js frontend connects to the FastAPI backend for the Bibliography management system.

## Overview

- **Frontend**: Next.js 15 with TypeScript (located in `/frontend/nextjs-app/`)
- **Backend**: FastAPI with Python 3.12+ (located in `/backend/`)
- **Database**: PostgreSQL with pgvector extension
- **Authentication**: JWT-based authentication via fastapi-users

## Quick Start

### 1. Start the Backend

```bash
cd backend
python main.py --reload
```

The backend will be available at: `http://localhost:8000`
API documentation at: `http://localhost:8000/docs`

### 2. Start the Frontend

```bash
cd frontend/nextjs-app
npm run dev
```

The frontend will be available at: `http://localhost:3000`

## Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost/bibliography_db
SECRET_KEY=your-secret-key-here
AUTH_TYPE=basic
EMBEDDING_MODEL=openai://nomic-embed-text
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_API_KEY=ollama
PDF_STORAGE_ROOT=./data/pdfs
WATCHED_FOLDER=./data/watched
```

### Frontend Environment Variables

The `.env.local` file has been created in `frontend/nextjs-app/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production, update this to your deployed backend URL.

## API Integration

### Authentication Flow

The frontend uses JWT token-based authentication:

1. **Registration**: `POST /auth/register`
   ```typescript
   await api.register(name, email, password);
   ```

2. **Login**: `POST /auth/jwt/login`
   ```typescript
   await api.login(email, password);
   ```

3. **Get User**: `GET /users/me`
   - Automatically called after login
   - Token is stored in localStorage and added to all requests

### Papers API

All paper operations are authenticated and use the `/api/v1/papers/` prefix:

- **List Papers**: `GET /api/v1/papers/`
  ```typescript
  const result = await api.getPapers({
    search_space_id: 1,
    limit: 50,
    offset: 0
  });
  ```

- **Get Paper**: `GET /api/v1/papers/{id}`
  ```typescript
  const paper = await api.getPaper(paperId);
  ```

- **Search Papers**: `POST /api/v1/papers/search`
  ```typescript
  const results = await api.searchPapers('machine learning', searchSpaceId);
  ```

- **Upload Paper**: `POST /api/v1/papers/upload`
  ```typescript
  const result = await api.uploadPaper(file, searchSpaceId);
  ```

- **Download Paper**: `GET /api/v1/papers/{id}/download`
  ```typescript
  const blob = await api.downloadPaper(paperId);
  ```

- **View PDF**: `GET /api/v1/papers/{id}/pdf`
  ```typescript
  const blob = await api.getPaperPdf(paperId);
  ```

- **Delete Paper**: `DELETE /api/v1/papers/{id}`
  ```typescript
  await api.deletePaper(paperId);
  ```

- **Get Citation**: `POST /api/v1/papers/{id}/citation`
  ```typescript
  const citation = await api.getCitation(paperId, 'apa');
  ```

### Annotations API

All annotation operations use the `/api/v1/annotations/` prefix:

- **Get Paper Annotations**: `GET /api/v1/annotations/paper/{paperId}`
  ```typescript
  const result = await api.getAnnotations(paperId, includePrivate);
  ```

- **Get My Annotations**: `GET /api/v1/annotations/user/me`
  ```typescript
  const result = await api.getMyAnnotations(paperId, limit, offset);
  ```

- **Create Annotation**: `POST /api/v1/annotations/?paper_id={paperId}`
  ```typescript
  const annotation = await api.createAnnotation(paperId, {
    content: 'My note',
    annotation_type: 'note',
    page_number: 5,
    is_private: false
  });
  ```

- **Update Annotation**: `PUT /api/v1/annotations/{id}`
  ```typescript
  const updated = await api.updateAnnotation(annotationId, {
    content: 'Updated note'
  });
  ```

- **Delete Annotation**: `DELETE /api/v1/annotations/{id}`
  ```typescript
  await api.deleteAnnotation(annotationId);
  ```

- **Toggle Privacy**: `POST /api/v1/annotations/{id}/toggle-privacy`
  ```typescript
  const updated = await api.toggleAnnotationPrivacy(annotationId);
  ```

- **Search Annotations**: `POST /api/v1/annotations/search`
  ```typescript
  const results = await api.searchAnnotations('important', paperId);
  ```

## Data Types

### Paper

```typescript
interface Paper {
  id: number;
  title?: string;
  authors: string[];
  journal?: string;
  publication_year?: number;
  doi?: string;
  abstract?: string;
  keywords: string[];
  tags: string[];
  processing_status: string;
  created_at: string;
  // ... additional fields
}
```

### Annotation

```typescript
interface Annotation {
  id: number;
  content: string;
  annotation_type: 'note' | 'highlight' | 'bookmark';
  page_number?: number;
  x_coordinate?: number;
  y_coordinate?: number;
  color?: string;
  is_private: boolean;
  paper_id: number;
  user_id: string;
  created_at: string;
}
```

## Testing the Integration

### 1. Test Authentication

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"
```

### 2. Test Paper Upload

```bash
# Upload a PDF (requires auth token)
curl -X POST http://localhost:8000/api/v1/papers/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@paper.pdf" \
  -F "search_space_id=1" \
  -F "move_file=true"
```

### 3. Test Annotations

```bash
# Create an annotation
curl -X POST "http://localhost:8000/api/v1/annotations/?paper_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test annotation",
    "annotation_type": "note",
    "page_number": 1,
    "is_private": false
  }'
```

## CORS Configuration

The backend is configured to accept requests from all origins (useful for development). In production, update the CORS settings in `backend/app/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Error Handling

The API client automatically handles:

- **401 Unauthorized**: Clears auth token and redirects to login
- **Token Injection**: Adds Bearer token to all authenticated requests
- **Error Responses**: Returns error details from the backend

## Next Steps

1. Create a search space for organizing papers
2. Upload PDFs through the frontend
3. Add annotations to papers
4. Share annotations with team members by toggling privacy settings

## Troubleshooting

### CORS Errors

If you see CORS errors in the browser console:
- Ensure the backend is running
- Check that `NEXT_PUBLIC_API_URL` matches your backend URL
- Verify CORS middleware is configured in the backend

### Authentication Issues

If authentication fails:
- Check that you're using the correct email/password
- Verify the backend database is running
- Check browser console for detailed error messages

### Type Errors

If you encounter TypeScript type mismatches:
- Ensure frontend types match backend schemas
- Check `types/index.ts` and `backend/app/schemas/papers.py`
- Rebuild the frontend: `npm run build`

## API Documentation

Full API documentation is available at: `http://localhost:8000/docs` when the backend is running.
