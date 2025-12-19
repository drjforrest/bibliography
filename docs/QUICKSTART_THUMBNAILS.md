# Quick Start: Thumbnails & PDF Viewing

## What You Need to Do

### 1. Install the Missing Dependency

```bash
cd backend
pip install Pillow
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 2. Test the Setup

```bash
python test_thumbnail_setup.py
```

This will verify everything is working and show you stats.

### 3. Start Your Servers

**Terminal 1 - Backend:**
```bash
cd backend
python main.py --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend/nextjs-app
npm run dev
```

### 4. View Your Library

Open http://localhost:3000/library

You should now see:
- ✅ Thumbnails of your PDF first pages (instead of purple gradients)
- ✅ Click any paper to view the full PDF
- ✅ Zoom controls in the PDF viewer

### 5. (Optional) Generate All Thumbnails at Once

If you want to pre-generate thumbnails for all papers:

```bash
# You'll need your auth token (get it from browser localStorage)
curl -X POST http://localhost:8000/api/v1/papers/thumbnails/generate-batch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "limit=100"
```

## What Changed

### Backend
- ✅ New thumbnail generator service
- ✅ Three new API endpoints for thumbnails
- ✅ Thumbnails stored in `data/thumbnails/`

### Frontend
- ✅ BookCard now shows real PDF thumbnails
- ✅ PDFViewer displays actual PDFs (not just text)
- ✅ Graceful fallbacks if PDFs aren't available

## File Locations

- **PDFs**: `data/pdfs/YYYY/MM/{uuid}.pdf`
- **Thumbnails**: `data/thumbnails/YYYY/MM/{paper_id}.jpg`

## Troubleshooting

**Thumbnails not showing?**
- Check backend logs for errors
- Verify PDF files exist in `data/pdfs/`
- Try regenerating: `curl .../papers/123/thumbnail?regenerate=true`

**PDF viewer not working?**
- Check browser console for errors
- Verify you're logged in (token in localStorage)
- Try a different browser

**Need more help?**
See the full documentation in `THUMBNAIL_PDF_SETUP.md`
