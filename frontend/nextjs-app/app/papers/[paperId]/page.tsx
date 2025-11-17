'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import AnnotationSidebar from '@/components/annotations/AnnotationSidebar';
import AnnotationToolbar from '@/components/annotations/AnnotationToolbar';
import InteractivePDFViewer from '@/components/annotations/InteractivePDFViewer';
import Header from '@/components/layout/Header';
import { api } from '@/lib/api';
import type { Annotation, AnnotationType, Paper } from '@/types';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function PaperAnnotationPage() {
  const params = useParams();
  const paperId = params.paperId as string;
  const [paper, setPaper] = useState<Paper | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [activeTool, setActiveTool] = useState<AnnotationType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Fetch paper and annotations on mount
  useEffect(() => {
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

    if (paperId) {
      fetchData();
    }
  }, [paperId]);

  const handleToolSelect = (tool: AnnotationType | 'zoom_in' | 'zoom_out') => {
    if (tool === 'zoom_in' || tool === 'zoom_out') {
      // Zoom is handled by the PDF viewer itself
      return;
    }
    // Set active tool for interactive PDF viewer
    if (tool === 'highlight' || tool === 'underline' || tool === 'comment') {
      setActiveTool(tool);
    }
  };

  const handleAnnotationCreate = async (annotation: any) => {
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
              <>
                {/* Article Summary Section - Collapsible */}
                {paper?.summary && (
                  <div className="flex-shrink-0 mx-4 mt-4 mb-2">
                    <div className="p-4 bg-[#4e989e]/10 dark:bg-[#4e989e]/20 border-l-4 border-[#4e989e] rounded-r-lg">
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <span className="material-symbols-outlined text-base text-[#4e989e]">summarize</span>
                        Article Summary
                      </h3>
                      <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap mt-2">
                        {paper.summary}
                      </p>
                    </div>
                  </div>
                )}
                
                {/* PDF Viewer with Floating Toolbar */}
                <div className="flex-1 min-h-0 flex relative">
                  {/* Floating Toolbar */}
                  <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-20">
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg">
                      <AnnotationToolbar onToolSelect={handleToolSelect} />
                    </div>
                  </div>
                  
                  <InteractivePDFViewer
                    pdfUrl={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/papers/${paperId}/pdf`}
                    activeTool={activeTool}
                    onAnnotationCreate={handleAnnotationCreate}
                    existingAnnotations={[]}
                  />
                </div>
              </>
            )}
          </div>

          {/* Right Sidebar: Annotations - Collapsible */}
          <div className={`relative transition-all duration-300 ${isSidebarOpen ? 'w-96' : 'w-0'}`}>
            {isSidebarOpen && (
              <AnnotationSidebar
                annotations={annotations}
                paperTitle={paper?.title || 'Document'}
              />
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
