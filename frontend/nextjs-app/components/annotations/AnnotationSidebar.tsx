'use client';

import { useState } from 'react';
import type { Annotation } from '@/types';
import AnnotationCard from './AnnotationCard';

interface AnnotationSidebarProps {
  annotations: Annotation[];
  paperTitle: string;
  paperSummary?: string;
}

export default function AnnotationSidebar({ annotations, paperTitle, paperSummary }: AnnotationSidebarProps) {
  const [filter, setFilter] = useState<'all' | 'page' | 'date'>('all');
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(true);

  return (
    <aside className="w-96 shrink-0 border-l border-gray-200 dark:border-gray-700 bg-background-light dark:bg-background-dark overflow-y-auto">
      <div className="p-6">
        {/* Summary Section - Always visible at top */}
        <div className="mb-6 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <span className="material-symbols-outlined text-base text-[#4e989e]">label</span>
              {paperTitle}
            </h3>
            <button
              onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <span className="material-symbols-outlined text-base">
                {isSummaryExpanded ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>
          {isSummaryExpanded && (
            <div className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg">
              {paperSummary ? (
                <p className="whitespace-pre-wrap">{paperSummary}</p>
              ) : (
                <p className="text-gray-400 dark:text-gray-500">No summary available</p>
              )}
            </div>
          )}
        </div>

        {/* Collaborative Annotations Section */}
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">Collaborative Annotations</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{paperTitle}</p>

        {/* Filter Buttons */}
        <div className="flex gap-2 flex-wrap mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`flex h-8 items-center justify-center gap-x-2 rounded-lg px-3 ${
              filter === 'all'
                ? 'bg-[#4e989e]/10 dark:bg-[#4e989e]/20 text-[#4e989e] dark:text-[#94d2bd] font-semibold'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <p className="text-sm">All</p>
          </button>
          <button
            onClick={() => setFilter('page')}
            className={`flex h-8 items-center justify-center gap-x-2 rounded-lg pl-3 pr-2 ${
              filter === 'page'
                ? 'bg-[#4e989e]/10 dark:bg-[#4e989e]/20 text-[#4e989e] dark:text-[#94d2bd] font-semibold'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">By Page</p>
            <span className="material-symbols-outlined text-base">expand_more</span>
          </button>
          <button
            onClick={() => setFilter('date')}
            className={`flex h-8 items-center justify-center gap-x-2 rounded-lg pl-3 pr-2 ${
              filter === 'date'
                ? 'bg-[#4e989e]/10 dark:bg-[#4e989e]/20 text-[#4e989e] dark:text-[#94d2bd] font-semibold'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">By Date</p>
            <span className="material-symbols-outlined text-base">expand_more</span>
          </button>
        </div>

        {/* Annotations List */}
        <div className="space-y-6">
          {annotations.length === 0 ? (
            <div className="text-center py-8">
              <span className="material-symbols-outlined text-4xl text-gray-300 dark:text-gray-600 mb-2">
                comment
              </span>
              <p className="text-sm text-gray-500 dark:text-gray-400">No annotations yet</p>
            </div>
          ) : (
            annotations.map((annotation) => (
              <AnnotationCard key={annotation.id} annotation={annotation} />
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
