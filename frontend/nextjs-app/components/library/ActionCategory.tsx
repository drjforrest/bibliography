'use client';

import type { ActionCategory, PaperAction } from '@/types/actions';
import { categoryMetadata } from '@/types/actions';
import { useState } from 'react';
import ActionCard from './ActionCard';

interface ActionCategoryProps {
  category: ActionCategory;
  actions: PaperAction[];
  paperCount?: number;
  defaultExpanded?: boolean;
}

export default function ActionCategory({ 
  category, 
  actions, 
  paperCount = 1,
  defaultExpanded = true 
}: ActionCategoryProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const metadata = categoryMetadata[category];

  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      {/* Category Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-label={`${metadata.label} category with ${actions.length} actions`}
        className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-[#4e989e] dark:text-[#94d2bd]">
            {metadata.icon}
          </span>
          <h2 className="font-semibold text-gray-900 dark:text-gray-100">
            {metadata.label}
          </h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({actions.length})
          </span>
        </div>
        <span className="material-symbols-outlined text-[20px] text-gray-500 dark:text-gray-400 transition-transform">
          {isExpanded ? 'expand_less' : 'expand_more'}
        </span>
      </button>

      {/* Actions Grid */}
      {isExpanded && (
        <div className="mt-2 grid grid-cols-1 gap-3 pl-1">
          {actions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              paperCount={paperCount}
            />
          ))}
        </div>
      )}
    </div>
  );
}
