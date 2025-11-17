'use client';

import { useState } from 'react';
import type { AnnotationType } from '@/types';

interface AnnotationToolbarProps {
  onToolSelect: (tool: AnnotationType) => void;
}

export default function AnnotationToolbar({ onToolSelect }: AnnotationToolbarProps) {
  const [activeTool, setActiveTool] = useState<string | null>(null);

  const handleToolClick = (tool: AnnotationType) => {
    setActiveTool(tool);
    onToolSelect(tool);
  };

  const tools = [
    { id: 'highlight', icon: 'format_ink_highlighter', label: 'Highlight' },
    { id: 'underline', icon: 'format_underlined', label: 'Underline' },
    { id: 'comment', icon: 'add_comment', label: 'Add Comment' },
  ];

  return (
    <div className="flex gap-2 p-2">
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
    </div>
  );
}
