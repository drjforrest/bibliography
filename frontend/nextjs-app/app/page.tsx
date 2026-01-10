"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/layout/Sidebar";
import BookGrid from "@/components/library/BookGrid";
import ChatPanel from "@/components/library/ChatPanel";
import LiteratureTypeFilter from "@/components/library/LiteratureTypeFilter";
import SearchBar from "@/components/library/SearchBar";
import ViewToggle from "@/components/library/ViewToggle";
import { createAuthenticatedClient, useApi } from "@/lib/api";
import type { LiteratureType, Paper, SortOption, Tag, Topic, ViewMode } from "@/types";
import { DndContext, DragEndEvent } from "@dnd-kit/core";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { useTagLiteratureTypesCache } from "@/hooks/useTagLiteratureTypesCache";
import { findTagInTopics, validateTagAssignment } from "@/lib/dragDropValidation";

export default function HomePage() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLiteratureType, setSelectedLiteratureType] = useState<LiteratureType | 'ALL'>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>();
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [dragFeedback, setDragFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Create authenticated API client - only when Clerk is loaded and getToken is available
  const authenticatedApi = useMemo(() => {
    if (!isLoaded || typeof getToken !== 'function') {
      // Return null to indicate client is not ready yet
      // This will prevent API calls until Clerk is initialized
      return null;
    }
    try {
      return createAuthenticatedClient(getToken);
    } catch (error) {
      console.error('Failed to create authenticated API client:', error);
      return null;
    }
  }, [isLoaded, getToken]);

  // API hook for tag operations
  const api = useApi();
  const { calculateTagLiteratureTypes, invalidateCache } = useTagLiteratureTypesCache();

  // Fetch papers and tags on mount (only when authenticated)
  useEffect(() => {
    if (!isLoaded) {
      return; // Keep loading state active while auth initializes
    }
    if (!isSignedIn) {
      setIsLoading(false);
      return;
    }
    if (!authenticatedApi) {
      // Wait for authenticated API client to be created
      return;
    }

    const fetchData = async () => {
      // authenticatedApi is guaranteed to be non-null here due to check above
      const api = authenticatedApi!;
      try {
        setIsLoading(true);
        const [papersData, tagsData] = await Promise.all([
          api.get('/api/v1/papers', {
            params: {
              limit: 100,
              literature_type: selectedLiteratureType === 'ALL' ? undefined : selectedLiteratureType,
            }
          }).then(r => r.data),
          api.get('/api/v1/tags/hierarchy').then(r => r.data),
        ]);
        setPapers(papersData.papers || []);
        
        // Convert tags to topics format for sidebar and calculate dominant literature types
        const convertedTopics = await calculateTagLiteratureTypes(tagsData.tags || []);
        setTopics(convertedTopics);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [isLoaded, isSignedIn, selectedLiteratureType, authenticatedApi, calculateTagLiteratureTypes]);

  const handleSearch = async (query: string) => {
    if (!authenticatedApi) return;
    setSearchQuery(query);
    try {
      if (query) {
        const result = await authenticatedApi.post('/api/v1/papers/search', { query }).then(r => r.data);
        setPapers(result.papers || []);
      } else {
        const result = await authenticatedApi.get('/api/v1/papers', {
          params: {
            limit: 100,
            literature_type: selectedLiteratureType === 'ALL' ? undefined : selectedLiteratureType,
          }
        }).then(r => r.data);
        setPapers(result.papers || []);
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
  };

  const handleDelete = async () => {
    if (!authenticatedApi) return;
    // Refetch papers after deletion
    try {
      const result = await authenticatedApi.get('/api/v1/papers', {
        params: {
          limit: 100,
          literature_type: selectedLiteratureType === 'ALL' ? undefined : selectedLiteratureType,
        }
      }).then(r => r.data);
      setPapers(result.papers || []);
    } catch (error) {
      console.error('Failed to reload papers after deletion:', error);
    }
  };

  const handleSort = (option: SortOption) => {
    setSortBy(option);
    const sorted = [...papers].sort((a, b) => {
      switch (option) {
        case "title":
          return (a.title || "").localeCompare(b.title || "");
        case "author":
          const authorA = (a.authors && a.authors[0]) || "";
          const authorB = (b.authors && b.authors[0]) || "";
          return authorA.localeCompare(authorB);
        case "date":
        default:
          return (
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
      }
    });
    setPapers(sorted);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over) {
      return; // Dropped outside any drop zone
    }

    // Extract paper ID and tag ID from drag/drop IDs
    const paperIdMatch = active.id.toString().match(/^paper-(\d+)$/);
    const tagIdMatch = over.id.toString().match(/^tag-(\d+)$/);

    if (!paperIdMatch || !tagIdMatch) {
      return; // Invalid IDs
    }

    const paperId = parseInt(paperIdMatch[1], 10);
    const tagId = parseInt(tagIdMatch[1], 10);

    // Get paper and validate assignment
    const paper = papers.find(p => p.id === paperId);
    const tag = findTagInTopics(topics, tagId);

    const validation = validateTagAssignment(paper, tag);
    if (!validation.valid) {
      setDragFeedback({ 
        message: validation.errorMessage || 'Cannot assign tag', 
        type: 'error' 
      });
      setTimeout(() => setDragFeedback(null), 5000);
      return;
    }

    try {
      await api.addTagToPaper(paperId, tagId);
      setDragFeedback({ message: 'Tag assigned successfully', type: 'success' });
      
      // Invalidate cache for this tag so it refreshes on next load
      invalidateCache(tagId);
      
      // Clear feedback after 3 seconds
      setTimeout(() => setDragFeedback(null), 3000);
    } catch (error: any) {
      console.error('Failed to assign tag:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to assign tag';
      setDragFeedback({ message: errorMessage, type: 'error' });
      
      // Clear feedback after 5 seconds for errors
      setTimeout(() => setDragFeedback(null), 5000);
    }
  };

  return (
    <ProtectedRoute>
      <DndContext onDragEnd={handleDragEnd}>
        <div className="flex min-h-screen bg-background-light dark:bg-background-dark">
          <Sidebar topics={topics} />

        <main className="flex-1 p-6">
            <div className="flex flex-col h-full">
              {/* Search and View Toggle */}
              <div className="flex items-center mb-6 gap-4">
                <div className="flex-1 max-w-2xl">
                  <SearchBar onSearch={handleSearch} />
                </div>
                <div className="flex items-center gap-2">
                  <ViewToggle view={viewMode} onViewChange={setViewMode} />
                  <button
                    onClick={() => {
                      setSelectedDocumentId(undefined);
                      setChatMessages([]); // Clear messages for general library chat
                      setIsChatOpen(true);
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-[#4e989e] hover:bg-[#3d7a7f] text-white rounded-lg transition-colors"
                  >
                    <span className="material-symbols-outlined text-base">chat</span>
                    <span className="hidden sm:inline">AI Chat</span>
                  </button>
                </div>
              </div>

              {/* Literature Type Filter */}
              <div className="mb-4">
                <LiteratureTypeFilter
                  selectedType={selectedLiteratureType}
                  onTypeChange={setSelectedLiteratureType}
                />
              </div>

              {/* Sort Options */}
              <div className="flex gap-3 pb-4 flex-wrap">
                <button
                  onClick={() => handleSort("date")}
                  className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                    sortBy === "date"
                      ? "bg-[#4e989e] text-white"
                      : "bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700"
                  }`}
                >
                  <p className="text-sm font-medium leading-normal">
                    Sort by Date
                  </p>
                  <span className="material-symbols-outlined text-base">
                    arrow_drop_down
                  </span>
                </button>
                <button
                  onClick={() => handleSort("title")}
                  className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                    sortBy === "title"
                      ? "bg-[#4e989e] text-white"
                      : "bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700"
                  }`}
                >
                  <p className="text-sm font-medium leading-normal">
                    Sort by Title
                  </p>
                  <span className="material-symbols-outlined text-base">
                    arrow_drop_down
                  </span>
                </button>
                <button
                  onClick={() => handleSort("author")}
                  className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                    sortBy === "author"
                      ? "bg-[#4e989e] text-white"
                      : "bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700"
                  }`}
                >
                  <p className="text-sm font-medium leading-normal">
                    Sort by Author
                  </p>
                  <span className="material-symbols-outlined text-base">
                    arrow_drop_down
                  </span>
                </button>
              </div>

              {/* Papers Grid/List */}
              <div className="flex-1 overflow-y-auto">
                {isLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-gray-500 dark:text-gray-400">Loading papers...</p>
                  </div>
                ) : papers.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-gray-500 dark:text-gray-400">No papers found</p>
                  </div>
                ) : (
                  <BookGrid
                    papers={papers}
                    view={viewMode}
                    onChatWithDocument={(documentId) => {
                      setSelectedDocumentId(documentId);
                      setChatMessages([]); // Clear messages for new document chat
                      setIsChatOpen(true);
                    }}
                    onDelete={handleDelete}
                  />
                )}
              </div>
            </div>
          </main>

          <ChatPanel
            isOpen={isChatOpen}
            onToggle={() => setIsChatOpen(!isChatOpen)}
            selectedDocumentId={selectedDocumentId}
            initialMessages={chatMessages}
            onMessagesChange={setChatMessages}
          />
        </div>

        {/* Drag and Drop Feedback */}
        {dragFeedback && (
          <div
            className={`fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 transition-opacity ${
              dragFeedback.type === 'success'
                ? 'bg-green-500 text-white'
                : 'bg-red-500 text-white'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">
                {dragFeedback.type === 'success' ? 'check_circle' : 'error'}
              </span>
              <span className="text-sm font-medium">{dragFeedback.message}</span>
            </div>
          </div>
        )}
      </DndContext>
    </ProtectedRoute>
  );
}
