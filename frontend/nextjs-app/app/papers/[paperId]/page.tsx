'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import AnnotationSidebar from '@/components/annotations/AnnotationSidebar';
import GenerateContentPanel from '@/components/papers/GenerateContentPanel';
import Header from '@/components/layout/Header';
import { getApiBaseUrl, useApi } from '@/lib/api';
import type { Annotation, AnnotationType, Paper } from '@/types';
import { useAuth } from '@clerk/nextjs';
import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

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

  return (
    <ProtectedRoute>
      <div className="flex h-screen flex-col">
        <Header />

        <div className="flex flex-1 overflow-hidden">
          {/* Main Content: PDF Viewer */}
          <div className="flex-1 flex flex-col bg-white dark:bg-gray-900/50 relative">
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

          {/* Right Sidebar: Annotations + Generate Content - Collapsible */}
          <div className={`relative transition-all duration-300 ${isSidebarOpen ? 'w-96' : 'w-0'}`}>
            {isSidebarOpen && (
              <div className="h-full overflow-y-auto">
                <AnnotationSidebar
                  annotations={annotations}
                  paperTitle={paper?.title || 'Document'}
                  paperSummary={paper?.summary}
                  shortDescription={paper?.short_description}
                  laySummary={paper?.lay_summary}
                  insights={paper?.insights}
                />
                
                {/* Generate Content Panel */}
                <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                  <GenerateContentPanel 
                    paperId={parseInt(paperId)} 
                    paperTitle={paper?.title || 'Document'}
                  />
                </div>
              </div>
            )}
            
            {/* Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 p-2 rounded-l-lg shadow-lg z-30"
              title={isSidebarOpen ? 'Hide annotations' : 'Show annotations'}
            >
              <span className="material-symbols-outlined text-base">
                {isSidebarOpen ? 'chevron_right' : 'chevron_left'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
