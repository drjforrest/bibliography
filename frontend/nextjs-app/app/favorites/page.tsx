'use client';

import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/layout/Sidebar";
import BookGrid from "@/components/library/BookGrid";
import SearchBar from "@/components/library/SearchBar";
import ViewToggle from "@/components/library/ViewToggle";
import { useApi } from "@/lib/api";
import type { Paper, SortOption, Tag, Topic, ViewMode } from "@/types";
import { DndContext, DragEndEvent } from "@dnd-kit/core";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useTagLiteratureTypesCache } from "@/hooks/useTagLiteratureTypesCache";
import { findTagInTopics, validateTagAssignment } from "@/lib/dragDropValidation";

export default function FavoritesPage() {
  const { isLoaded, isSignedIn } = useAuth();
  const api = useApi();
  const { calculateTagLiteratureTypes, invalidateCache } = useTagLiteratureTypesCache();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [dragFeedback, setDragFeedback] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Fetch papers and tags on mount (only when authenticated)
  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [papersData, tagsData] = await Promise.all([
          api.getFavorites({ limit: 100 }),
          api.getTagHierarchy(),
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
  }, [isLoaded, isSignedIn, api]);

  const handleSearch = async (query: string) => {
    if (!isLoaded || !isSignedIn) return;
    
    setSearchQuery(query);
    try {
      if (query) {
        // Search within favorites
        const result = await api.getFavorites({ limit: 100 });
        const filteredPapers = (result.papers || []).filter((paper: Paper) =>
          paper.title?.toLowerCase()?.includes(query.toLowerCase()) ||
          paper.authors?.some((author: string) => author.toLowerCase().includes(query.toLowerCase()))
        );
        setPapers(filteredPapers);
      } else {
        // Show all favorites
        const result = await api.getFavorites({ limit: 100 });
        setPapers(result.papers || []);
      }
    } catch (error) {
      console.error('Search failed:', error);
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
      invalidateCache(tagId);
      setTimeout(() => setDragFeedback(null), 3000);
    } catch (error: any) {
      console.error('Failed to assign tag:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to assign tag';
      setDragFeedback({ message: errorMessage, type: 'error' });
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
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
                  Favorites
                </h1>
              </div>

              {/* Search and View Toggle */}
              <div className="flex items-center mb-6 gap-4">
                <div className="flex-1 max-w-2xl">
                  <SearchBar onSearch={handleSearch} />
                </div>
                <ViewToggle view={viewMode} onViewChange={setViewMode} />
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
                  <div className="flex items-center justify-center h-full flex-col gap-4">
                    <span className="material-symbols-outlined text-6xl text-gray-400">star_outline</span>
                    <p className="text-gray-500 dark:text-gray-400">No favorite papers yet</p>
                    <p className="text-sm text-gray-400 dark:text-gray-500">
                      Click the star icon on any paper to add it to your favorites
                    </p>
                  </div>
                ) : (
                  <BookGrid
                    papers={papers}
                    view={viewMode}
                    onFavoriteChange={async () => {
                      // Refresh favorites when a paper is unfavorited
                      try {
                        const result = await api.getFavorites({ limit: 100 });
                        setPapers(result.papers || []);
                      } catch (error) {
                        console.error('Failed to refresh favorites:', error);
                      }
                    }}
                    onDelete={async () => {
                      // Refresh favorites when a paper is deleted
                      try {
                        const result = await api.getFavorites({ limit: 100 });
                        setPapers(result.papers || []);
                      } catch (error) {
                        console.error('Failed to refresh favorites:', error);
                      }
                    }}
                  />
                )}
              </div>
            </div>
          </main>

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
      </div>
      </DndContext>
    </ProtectedRoute>
  );
}