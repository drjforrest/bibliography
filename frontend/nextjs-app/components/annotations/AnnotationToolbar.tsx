'use client';

import { useState } from 'react';
import type { AnnotationType } from '@/types';

interface AnnotationToolbarProps {
  onToolSelect: (tool: AnnotationType | 'zoom_in' | 'zoom_out') => void;
}

export default function AnnotationToolbar({ onToolSelect }: AnnotationToolbarProps) {
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const handleToolClick = (tool: AnnotationType | 'zoom_in' | 'zoom_out') => {
    setActiveTool(tool);
    onToolSelect(tool);
  };

  const tools = [
    { id: 'highlight', icon: 'format_ink_highlighter', label: 'Highlight' },
    { id: 'underline', icon: 'format_underlined', label: 'Underline' },
    { id: 'comment', icon: 'add_comment', label: 'Add Comment' },
  ];

  const zoomTools = [
    { id: 'zoom_in', icon: 'zoom_in', label: 'Zoom In' },
    { id: 'zoom_out', icon: 'zoom_out', label: 'Zoom Out' },
  ];

  return (
    <div className="sticky top-4 z-10 mx-auto mb-8 flex w-fit justify-center gap-2 rounded-lg bg-white dark:bg-gray-800 p-2 shadow-md border border-gray-200 dark:border-gray-700">
      {tools.map((tool) => (
        <button
          key={tool.id}
          onClick={() => handleToolClick(tool.id as AnnotationType)}
          className={`p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 ${
            activeTool === tool.id
              ? 'bg-primary/20 text-primary dark:bg-primary/30'
              : 'text-gray-700 dark:text-gray-300'
          }`}
          title={tool.label}
        >
          <span className="material-symbols-outlined">{tool.icon}</span>
        </button>
      ))}

      <div className="border-l border-gray-300 dark:border-gray-600 mx-2" />

      {zoomTools.map((tool) => (
        <button
          key={tool.id}
          onClick={() => handleToolClick(tool.id as 'zoom_in' | 'zoom_out')}
          className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          title={tool.label}
        >
          <span className="material-symbols-outlined">{tool.icon}</span>
        </button>
      ))}
    </div>
  );
}
