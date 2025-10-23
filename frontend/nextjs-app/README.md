# Bibliography Management System - Next.js Frontend

A modern, responsive web interface for the Bibliography Management System built with Next.js, TypeScript, and Tailwind CSS.

## Features

- **JWT Authentication**: Simple token-based authentication for lab members
- **Library Home**: Browse papers and books in grid or list view with search and sorting capabilities
- **Annotation Screen**: Collaborative PDF viewing with highlighting, underlining, and commenting features
- **Message Board**: Threaded discussion forum for team collaboration
- **Dark Mode**: Full dark mode support with theme persistence
- **Responsive Design**: Mobile-friendly interface using Tailwind CSS
- **Protected Routes**: Automatic redirection to login for unauthenticated users

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom theme
- **Icons**: Material Symbols Outlined
- **Fonts**: Inter (display), Merriweather (body)
- **API Client**: Axios for FastAPI backend integration

## Getting Started

### Prerequisites

- Node.js 18+ installed
- FastAPI backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
nextjs-app/
├── app/                    # Next.js app router pages
│   ├── layout.tsx         # Root layout with theme provider
│   ├── page.tsx           # Library home page
│   ├── papers/            # Paper annotation pages
│   │   └── [paperId]/
│   └── messages/          # Message board pages
├── components/            # React components
│   ├── layout/           # Sidebar, Header components
│   ├── library/          # Library-specific components
│   ├── annotations/      # Annotation components
│   └── messages/         # Message board components
├── lib/                  # Utilities and API client
│   └── api.ts           # FastAPI client
├── types/               # TypeScript type definitions
│   └── index.ts
└── public/              # Static assets
```

## Authentication

The application uses JWT (JSON Web Tokens) for authentication, designed for internal lab use:

### First Time Setup

1. Start the application and navigate to the registration page
2. Create an account with your name, email, and password
3. You'll be automatically logged in and redirected to the library

### Login Flow

- Visit `/auth/login` or you'll be redirected automatically if not authenticated
- Enter your email and password
- JWT token is stored in localStorage for persistent sessions
- Protected routes automatically redirect to login if token is missing/invalid

### User Features

- **User Menu**: Click your avatar in the sidebar or header to access user options
- **Logout**: Sign out from the user menu dropdown
- **Auto-login**: Token persists across browser sessions until logout

### API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`. The API client in `lib/api.ts` provides methods for:

- **Authentication**: Login, register, token refresh
- **Papers**: CRUD operations, search, favorites
- **Annotations**: Create, read, update, delete
- **Messages**: Topics and threaded discussions
- **DEVONthink**: Sync operations

All API requests automatically include the JWT token in the Authorization header.

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Features by Page

### Library Home (`/`)
- Grid/list view toggle
- Search functionality
- Sort by date, title, or author
- Topic navigation sidebar
- Dark mode toggle

### Annotation Screen (`/papers/[paperId]`)
- PDF viewer with zoom controls
- Annotation toolbar (highlight, underline, comment)
- Collaborative annotations sidebar
- Filter annotations by page or date

### Message Board (`/messages`)
- Topic-based discussions
- Threaded replies
- Real-time message composition
- Search topics

## Development

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format
```

## Deployment

The app can be deployed to Vercel, Netlify, or any platform supporting Next.js:

```bash
npm run build
npm start
```

## Contributing

This is part of a larger bibliography management system. See the main project README for contribution guidelines.

## License

See main project LICENSE file.
