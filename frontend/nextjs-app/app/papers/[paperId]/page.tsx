'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import AnnotationSidebar from '@/components/annotations/AnnotationSidebar';
import AnnotationToolbar from '@/components/annotations/AnnotationToolbar';
import PDFViewer from '@/components/annotations/PDFViewer';
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
      // Handle zoom
      return;
    }
    setActiveTool(tool);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen flex-col">
        <Header />

        <div className="flex flex-1 overflow-hidden">
          {/* Main Content: PDF Viewer */}
          <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-900/50 p-8 relative">
            <div className="max-w-4xl mx-auto">
              <AnnotationToolbar onToolSelect={handleToolSelect} />
              {isLoading ? (
                <div className="flex items-center justify-center h-96">
                  <p className="text-gray-500 dark:text-gray-400">Loading paper...</p>
                </div>
              ) : error ? (
                <div className="flex items-center justify-center h-96">
                  <p className="text-red-500 dark:text-red-400">{error}</p>
                </div>
              ) : (
                <PDFViewer
                  title={paper?.title || 'Document'}
                  content={paper?.abstract}
                />
              )}
            </div>
          </div>

          {/* Right Sidebar: Annotations */}
          <AnnotationSidebar
            annotations={annotations}
            paperTitle={paper?.title || 'Document'}
          />
        </div>
      </div>
    </ProtectedRoute>
  );
}
