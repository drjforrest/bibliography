"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/layout/Sidebar";
import BookGrid from "@/components/library/BookGrid";
import ChatPanel from "@/components/library/ChatPanel";
import SearchBar from "@/components/library/SearchBar";
import ViewToggle from "@/components/library/ViewToggle";
import LiteratureTypeFilter from "@/components/library/LiteratureTypeFilter";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import type { Paper, SortOption, Tag, Topic, ViewMode, LiteratureType } from "@/types";
import { useEffect, useState } from "react";

export default function HomePage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLiteratureType, setSelectedLiteratureType] = useState<LiteratureType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>();
  const [chatMessages, setChatMessages] = useState<any[]>([]);

  // Fetch papers and tags on mount (only when authenticated)
  useEffect(() => {
    if (!isAuthenticated || authLoading) {
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [papersData, tagsData] = await Promise.all([
          api.getPapers({ 
            limit: 100,
            literature_type: selectedLiteratureType || undefined,
          }),
          api.getTagHierarchy(),
        ]);
        setPapers(papersData.papers || []);
        
        // Convert tags to topics format for sidebar
        const convertedTopics: Topic[] = (tagsData.tags || []).map((tag: Tag) => ({
          id: tag.id.toString(),
          name: tag.name,
          children: tag.children?.map((child: Tag) => ({
            id: child.id.toString(),
            name: child.name,
          })),
        }));
        setTopics(convertedTopics);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [isAuthenticated, authLoading, selectedLiteratureType]);

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    try {
      if (query) {
        const result = await api.searchPapers(query);
        setPapers(result.papers || []);
      } else {
        const result = await api.getPapers({ 
          limit: 100,
          literature_type: selectedLiteratureType || undefined,
        });
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

  return (
    <ProtectedRoute>
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
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
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
                      ? "bg-primary text-white"
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
                      ? "bg-primary text-white"
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
                      ? "bg-primary text-white"
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
    </ProtectedRoute>
  );
}
