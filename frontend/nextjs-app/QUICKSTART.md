# Quick Start Guide

## Getting Your Bibliography System Running

### Prerequisites

- Node.js 18+ installed
- FastAPI backend running on `http://localhost:8000`
- PostgreSQL database with pgvector extension

### Step 1: Install Dependencies

```bash
cd frontend/nextjs-app
npm install
```

### Step 2: Configure Environment

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Start the Development Server

```bash
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### Step 4: First Login

1. You'll be automatically redirected to `/auth/login`
2. Click **"Create an account"** to register
3. Fill in:
   - Your full name
   - Lab email address
   - Password (minimum 8 characters)
4. Click **"Create account"**
5. You'll be automatically logged in and redirected to the library

### Step 5: Explore the Interface

#### Library Home (`/`)
- View all papers in grid or list mode
- Search by title or author
- Sort by date, title, or author
- Browse by topics in the sidebar
- Click any paper to view annotations

#### Annotation Screen (`/papers/:id`)
- View PDF content
- Use toolbar to highlight, underline, or comment
- See collaborative annotations in the right sidebar
- Filter annotations by page or date

#### Message Board (`/messages`)
- Participate in topic-based discussions
- Reply to messages (threaded)
- Search topics
- Create new discussion topics

### User Management

**Access User Menu:**
- Click your avatar in the sidebar (left) or header (top-right)
- View your profile information
- Click "Sign out" to logout

**Password Security:**
- Minimum 8 characters required
- Stored securely with bcrypt hashing in the backend
- JWT tokens expire based on backend configuration

### Troubleshooting

**Can't connect to backend:**
```bash
# Check if FastAPI is running
curl http://localhost:8000/api/v1/health

# If not, start the backend:
cd backend
python main.py --reload
```

**Login fails with 401:**
- Check your credentials
- Ensure backend authentication is configured
- Verify database is running

**Blank screen or loading forever:**
- Check browser console for errors
- Clear localStorage: `localStorage.clear()`
- Refresh the page

**Build errors:**
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Production Deployment

```bash
# Build for production
npm run build

# Start production server
npm start
```

The production build will be optimized and ready to deploy on your home server.

### Lab-Only Deployment Notes

Since this is for internal lab use:

1. **No public exposure needed** - Keep it on your internal network
2. **Simple authentication** - JWT is sufficient for trusted lab members
3. **Backup strategy** - Ensure PostgreSQL backups include user accounts
4. **Access control** - Use firewall rules to restrict access to lab network

### Next Steps

1. **Import your papers**: Use the DEVONthink sync feature
2. **Invite lab members**: Share registration link with team
3. **Create topics**: Organize papers by research areas
4. **Start collaborating**: Add annotations and discuss papers

### Support

For issues or questions:
- Check the main README.md for detailed documentation
- Review FastAPI backend logs for API errors
- Check browser developer console for frontend errors

Happy researching! 📚
