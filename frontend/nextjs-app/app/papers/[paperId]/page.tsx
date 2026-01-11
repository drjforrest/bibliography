'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import AnnotationSidebar from '@/components/annotations/AnnotationSidebar';
import Header from '@/components/layout/Header';
import ActionButton from '@/components/library/ActionButton';
import ChatPanel from '@/components/library/ChatPanel';
import PaperActionPanel from '@/components/library/PaperActionPanel';
import { RecommendationsModal } from '@/components/library/RecommendationsModal';
import { getApiBaseUrl, useApi } from '@/lib/api';
import type { Annotation, AnnotationType, Paper } from '@/types';
import { useAuth } from '@clerk/nextjs';
import dynamic from 'next/dynamic';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

// Dynamically import InteractivePDFViewer to prevent SSR issues with PDF.js
const InteractivePDFViewer = dynamic(
  () => import('@/components/annotations/InteractivePDFViewer'),
  { ssr: false }
);

export default function PaperAnnotationPage() {
  const params = useParams();
  const paperId = params.paperId as string;
  const { isLoaded, isSignedIn } = useAuth();
  const api = useApi();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [activeTool, setActiveTool] = useState<AnnotationType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarView, setSidebarView] = useState<'annotations' | 'chat'>('annotations');
  const [showActionPanel, setShowActionPanel] = useState(false);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const actionButtonRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Fetch paper and annotations on mount (only when authenticated)
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !paperId) {
      if (isLoaded && !isSignedIn) {
        setIsLoading(false);
        setError('Please sign in to view papers');
      }
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [paperData, annotationsData] = await Promise.all([
          api.getPaper(parseInt(paperId)),
          api.getAnnotations(parseInt(paperId)),
        ]);

        // Parse insights if they come as a JSON string
        // TODO: Investigate and fix the backend so insights are returned as an actual array rather than a JSON string
        if (paperData?.insights && typeof paperData.insights === 'string') {
          try {
            paperData.insights = JSON.parse(paperData.insights);
          } catch (e) {
            // If parsing fails, try to extract array from string using regex (non-greedy to match first array)
            const match = paperData.insights.match(/\[.*?\]/s);
            if (match) {
              try {
                paperData.insights = JSON.parse(match[0]);
              } catch (e2) {
                console.warn('Failed to parse insights:', e2);
                paperData.insights = [];
              }
            } else {
              paperData.insights = [];
            }
          }
        }

        setPaper(paperData);
        setAnnotations(annotationsData.annotations || []);
      } catch (err) {
        console.error('Failed to fetch paper data:', err);
        setError('Failed to load paper and annotations');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [paperId, isLoaded, isSignedIn, api]);

  const handleToolSelect = (tool: AnnotationType) => {
    // Set active tool for interactive PDF viewer
    setActiveTool(tool);
  };

  const handleAnnotationCreate = async (annotation: any) => {
    if (!isLoaded || !isSignedIn) {
      console.error('User not authenticated');
      return;
    }

    try {
      // Save to backend
      await api.createAnnotation(parseInt(paperId), {
        content: annotation.content || '',
        page_number: annotation.page,
        annotation_type: annotation.type,
        is_private: true,
        // Store coordinates as JSON in content for now
        // In production, you'd extend the API to support coordinates
      });
      
      // Refresh annotations
      const annotationsData = await api.getAnnotations(parseInt(paperId));
      setAnnotations(annotationsData.annotations || []);
    } catch (error) {
      console.error('Failed to save annotation:', error);
    }
  };

  const handleActionComplete = (actionId: string) => {
    switch (actionId) {
      case 'find-related':
        if (paper) {
          setShowRecommendations(true);
        }
        break;
      case 'chat-with-pdf':
        setSidebarView('chat');
        setIsSidebarOpen(true);
        break;
      case 'delete':
        // Navigate back to library after deletion
        router.push('/');
        break;
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen flex-col">
        <Header />

        <div className="flex flex-1 overflow-hidden">
          {/* Main Content: PDF Viewer */}
          <div className="flex-1 flex flex-col bg-white dark:bg-gray-900/50 relative">
            {/* Toolbar with Action Button */}
            {paper && !isLoading && !error && (
              <div className="absolute top-4 right-4 z-10" ref={actionButtonRef}>
                <ActionButton
                  onClick={() => setShowActionPanel(true)}
                  variant="default"
                  label="Actions"
                />
              </div>
            )}
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500 dark:text-gray-400">Loading paper...</p>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-red-500 dark:text-red-400">{error}</p>
              </div>
            ) : (
              <InteractivePDFViewer
                pdfUrl={`${getApiBaseUrl()}/api/v1/papers/${paperId}/pdf`}
                activeTool={activeTool}
                onToolSelect={handleToolSelect}
                onAnnotationCreate={handleAnnotationCreate}
                existingAnnotations={[]}
              />
            )}
          </div>

          {/* Right Sidebar: Annotations/Chat - Collapsible */}
          <div className={`relative transition-all duration-300 h-full ${isSidebarOpen ? 'w-96' : 'w-0'}`}>
            {isSidebarOpen && (
              <div className="h-full w-96 shrink-0 border-l border-gray-200 dark:border-gray-700 bg-background-light dark:bg-background-dark flex flex-col overflow-hidden">
                {/* Tab Switcher */}
                <div className="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <button
                    onClick={() => setSidebarView('annotations')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                      sidebarView === 'annotations'
                        ? 'bg-white dark:bg-gray-800 text-[#4e989e] dark:text-[#94d2bd] border-b-2 border-[#4e989e]'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                    }`}
                  >
                    <span className="material-symbols-outlined text-base align-middle mr-2">comment</span>
                    Annotations
                  </button>
                  <button
                    onClick={() => setSidebarView('chat')}
                    className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                      sidebarView === 'chat'
                        ? 'bg-white dark:bg-gray-800 text-[#4e989e] dark:text-[#94d2bd] border-b-2 border-[#4e989e]'
                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                    }`}
                  >
                    <span className="material-symbols-outlined text-base align-middle mr-2">chat</span>
                    Chat
                  </button>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-hidden">
                  {sidebarView === 'annotations' ? (
                    <AnnotationSidebar
                      annotations={annotations}
                      paperTitle={paper?.title || 'Document'}
                      paperSummary={paper?.summary}
                      shortDescription={paper?.short_description}
                      laySummary={paper?.lay_summary}
                      insights={paper?.insights}
                    />
                  ) : (
                    <ChatPanel
                      isOpen={true}
                      onToggle={() => setSidebarView('annotations')}
                      selectedDocumentId={paper?.id}
                      embedded={true}
                    />
                  )}
                </div>
              </div>
            )}
            
            {/* Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 p-2 rounded-l-lg shadow-lg z-30"
              title={isSidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
            >
              <span className="material-symbols-outlined text-base">
                {isSidebarOpen ? 'chevron_right' : 'chevron_left'}
              </span>
            </button>
          </div>
        </div>

        {/* Action Panel - Floating Dropdown */}
        {paper && (
          <PaperActionPanel
            paper={paper}
            isOpen={showActionPanel}
            onClose={() => setShowActionPanel(false)}
            onActionComplete={handleActionComplete}
            buttonRef={actionButtonRef}
          />
        )}

        {/* Recommendations Modal */}
        {paper && showRecommendations && (
          <RecommendationsModal
            paperId={paper.id}
            paperTitle={paper.title}
            onClose={() => setShowRecommendations(false)}
          />
        )}

      </div>
    </ProtectedRoute>
  );
}
