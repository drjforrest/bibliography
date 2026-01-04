'use client';

import type { AnnotationType } from '@/types';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

// @ts-ignore
import 'react-pdf/dist/Page/AnnotationLayer.css';
// @ts-ignore
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker - use self-hosted worker instead of CDN for security
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
}

interface Annotation {
  id: string;
  type: AnnotationType;
  page: number;
  rect: { x: number; y: number; width: number; height: number };
  color?: string;
  content?: string;
  timestamp: Date;
}

interface InteractivePDFViewerProps {
  pdfUrl: string;
  activeTool: AnnotationType | null;
  onToolSelect: (tool: AnnotationType) => void;
  onAnnotationCreate: (annotation: Omit<Annotation, 'id' | 'timestamp'>) => void;
  existingAnnotations?: Annotation[];
}

export default function InteractivePDFViewer({
  pdfUrl,
  activeTool,
  onToolSelect,
  onAnnotationCreate,
  existingAnnotations = [],
}: InteractivePDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(0.9);
  const [selection, setSelection] = useState<any>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
  const [currentRect, setCurrentRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>(existingAnnotations);
  const [toolbarPosition, setToolbarPosition] = useState<{ x: number; y: number }>({ x: 16, y: 16 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [activeToolLocal, setActiveToolLocal] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAnnotations(existingAnnotations);
  }, [existingAnnotations]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoadError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setLoadError(`Failed to load PDF file: ${error.message || 'Unknown error'}`);
  };

  const handleZoom = (direction: 'in' | 'out') => {
    setScale((prev) => {
      if (direction === 'in') return Math.min(prev + 0.2, 3);
      return Math.max(prev - 0.2, 0.5);
    });
  };

  const handleToolClick = (tool: AnnotationType) => {
    setActiveToolLocal(tool);
    onToolSelect(tool);
  };

  // Handle text selection for highlight/underline
  const handleTextSelection = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || !activeTool) return;

    const range = sel.getRangeAt(0);
    if (range.collapsed) return;

    const rect = range.getBoundingClientRect();
    const pageRect = pageRef.current?.getBoundingClientRect();
    
    if (!pageRect) return;

    // Convert to PDF coordinates relative to page
    const relativeRect = {
      x: (rect.left - pageRect.left) / scale,
      y: (rect.top - pageRect.top) / scale,
      width: rect.width / scale,
      height: rect.height / scale,
    };

    if (activeTool === 'highlight' || activeTool === 'underline') {
      const newAnnotation = {
        type: activeTool,
        page: pageNumber,
        rect: relativeRect,
        color: activeTool === 'highlight' ? '#ffff00' : '#ff0000',
        content: sel.toString(),
      };

      onAnnotationCreate(newAnnotation);
      setAnnotations((prev) => [
        ...prev,
        { ...newAnnotation, id: Date.now().toString(), timestamp: new Date() },
      ]);

      // Clear selection
      sel.removeAllRanges();
    }
  }, [activeTool, pageNumber, scale, onAnnotationCreate]);

  // Handle mouse events for comment tool
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (activeTool === 'comment') {
      const pageRect = pageRef.current?.getBoundingClientRect();
      if (!pageRect) return;

      const x = (e.clientX - pageRect.left) / scale;
      const y = (e.clientY - pageRect.top) / scale;

      // Prompt for comment text
      const content = prompt('Enter your comment:');
      if (content) {
        const newAnnotation = {
          type: 'comment' as AnnotationType,
          page: pageNumber,
          rect: { x, y, width: 24, height: 24 },
          content,
          color: '#4A90E2',
        };

        onAnnotationCreate(newAnnotation);
        setAnnotations((prev) => [
          ...prev,
          { ...newAnnotation, id: Date.now().toString(), timestamp: new Date() },
        ]);
      }
    }
  };

  // Handle dragging the toolbar
  const handleToolbarMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (toolbarRef.current) {
      const rect = toolbarRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      setIsDragging(true);
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect();
        const newX = Math.max(0, Math.min(e.clientX - containerRect.left - dragOffset.x, containerRect.width - (toolbarRef.current?.offsetWidth || 0)));
        const newY = Math.max(0, Math.min(e.clientY - containerRect.top - dragOffset.y, containerRect.height - (toolbarRef.current?.offsetHeight || 0)));
        setToolbarPosition({ x: newX, y: newY });
      }
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
      }
      if (activeTool === 'highlight' || activeTool === 'underline') {
        setTimeout(() => handleTextSelection(), 10);
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [activeTool, handleTextSelection, isDragging, dragOffset]);

  return (
    <div ref={containerRef} className="w-full h-full flex flex-col bg-gray-100 dark:bg-gray-900 relative">
      {/* Unified Draggable Controls */}
      <div
        ref={toolbarRef}
        className="absolute z-20 bg-white dark:bg-gray-800 rounded-lg shadow-lg"
        style={{
          left: `${toolbarPosition.x}px`,
          top: `${toolbarPosition.y}px`,
          cursor: isDragging ? 'grabbing' : 'grab',
        }}
      >
        {/* Drag Handle */}
        <div
          className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700"
          onMouseDown={handleToolbarMouseDown}
        >
          <span className="material-symbols-outlined text-sm text-gray-400">drag_indicator</span>
          <span className="text-xs text-gray-500 dark:text-gray-400 select-none">Drag to move</span>
        </div>
        
        {/* Controls Container */}
        <div className="p-2 flex flex-col gap-2">
          {/* Annotation Tools */}
          <div className="flex gap-2">
            <button
              onClick={() => handleToolClick('highlight')}
              className={`p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                activeToolLocal === 'highlight'
                  ? 'bg-primary/20 text-primary dark:bg-primary/30'
                  : 'text-gray-700 dark:text-gray-300'
              }`}
              title="Highlight"
            >
              <span className="material-symbols-outlined">format_ink_highlighter</span>
            </button>
            <button
              onClick={() => handleToolClick('underline')}
              className={`p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                activeToolLocal === 'underline'
                  ? 'bg-primary/20 text-primary dark:bg-primary/30'
                  : 'text-gray-700 dark:text-gray-300'
              }`}
              title="Underline"
            >
              <span className="material-symbols-outlined">format_underlined</span>
            </button>
            <button
              onClick={() => handleToolClick('comment')}
              className={`p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
                activeToolLocal === 'comment'
                  ? 'bg-primary/20 text-primary dark:bg-primary/30'
                  : 'text-gray-700 dark:text-gray-300'
              }`}
              title="Add Comment"
            >
              <span className="material-symbols-outlined">add_comment</span>
            </button>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Zoom Controls */}
          <div className="flex gap-2 items-center">
            <button
              onClick={() => handleZoom('out')}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Zoom out"
            >
              <span className="material-symbols-outlined">zoom_out</span>
            </button>
            <span className="px-3 py-2 text-sm font-medium min-w-[60px] text-center">{Math.round(scale * 100)}%</span>
            <button
              onClick={() => handleZoom('in')}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              title="Zoom in"
            >
              <span className="material-symbols-outlined">zoom_in</span>
            </button>
          </div>

          {/* Divider */}
          <div className="border-t border-gray-200 dark:border-gray-700" />

          {/* Page Navigation */}
          <div className="flex gap-2 items-center">
            <button
              onClick={() => setPageNumber((prev) => Math.max(prev - 1, 1))}
              disabled={pageNumber <= 1}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50"
              title="Previous page"
            >
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <span className="px-2 text-sm font-medium min-w-[60px] text-center">
              {pageNumber} / {numPages}
            </span>
            <button
              onClick={() => setPageNumber((prev) => Math.min(prev + 1, numPages))}
              disabled={pageNumber >= numPages}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded disabled:opacity-50"
              title="Next page"
            >
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      </div>

      {/* PDF Document */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-8">
        {loadError ? (
          <div className="flex flex-col items-center justify-center h-full">
            <span className="material-symbols-outlined text-5xl text-red-400 dark:text-red-600 mb-4">
              error_outline
            </span>
            <p className="text-red-600 dark:text-red-400 text-lg font-medium mb-2">{loadError}</p>
            <p className="text-gray-600 dark:text-gray-400 text-sm">Please check the console for more details.</p>
            <button
              onClick={() => {
                setLoadError(null);
                window.location.reload();
              }}
              className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        ) : (
          <div
            ref={pageRef}
            className="relative"
            onMouseDown={handleMouseDown}
            style={{ cursor: activeTool === 'comment' ? 'crosshair' : 'default' }}
          >
            <Document 
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess} 
              onLoadError={onDocumentLoadError}
              loading={<LoadingSpinner />}
              options={{
                httpHeaders: {
                  'Accept': 'application/pdf',
                },
                withCredentials: false,
              }}
              error={
                <div className="flex flex-col items-center justify-center h-96">
                  <span className="material-symbols-outlined text-5xl text-red-400 dark:text-red-600 mb-4">
                    error_outline
                  </span>
                  <p className="text-red-600 dark:text-red-400">Failed to load PDF file</p>
                </div>
              }
            >
              <Page pageNumber={pageNumber} scale={scale} renderTextLayer={true} renderAnnotationLayer={false} />
            </Document>

          {/* Render annotation overlays */}
          <svg
            className="absolute top-0 left-0 w-full h-full pointer-events-none"
            style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
          >
            {annotations
              .filter((ann) => ann.page === pageNumber)
              .map((ann) => (
                <g key={ann.id}>
                  {ann.type === 'highlight' && (
                    <rect
                      x={ann.rect.x}
                      y={ann.rect.y}
                      width={ann.rect.width}
                      height={ann.rect.height}
                      fill={ann.color}
                      opacity={0.3}
                    />
                  )}
                  {ann.type === 'underline' && (
                    <line
                      x1={ann.rect.x}
                      y1={ann.rect.y + ann.rect.height}
                      x2={ann.rect.x + ann.rect.width}
                      y2={ann.rect.y + ann.rect.height}
                      stroke={ann.color}
                      strokeWidth={2}
                    />
                  )}
                  {ann.type === 'comment' && (
                    <g>
                      <circle cx={ann.rect.x + 12} cy={ann.rect.y + 12} r={12} fill={ann.color} />
                      <text
                        x={ann.rect.x + 12}
                        y={ann.rect.y + 16}
                        textAnchor="middle"
                        fill="white"
                        fontSize="14"
                        fontWeight="bold"
                      >
                        💬
                      </text>
                    </g>
                  )}
                </g>
              ))}
          </svg>
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>
  );
}
