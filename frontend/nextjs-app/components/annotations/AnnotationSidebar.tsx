'use client';

import { useState } from 'react';
import type { Annotation } from '@/types';
import AnnotationCard from './AnnotationCard';

interface AnnotationSidebarProps {
  annotations: Annotation[];
  paperTitle: string;
}

export default function AnnotationSidebar({ annotations, paperTitle }: AnnotationSidebarProps) {
  const [filter, setFilter] = useState<'all' | 'page' | 'date'>('all');

  return (
    <aside className="w-96 shrink-0 border-l border-gray-200 dark:border-gray-700 bg-background-light dark:bg-background-dark overflow-y-auto">
      <div className="p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Collaborative Annotations</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{paperTitle}</p>

        {/* Filter Buttons */}
        <div className="flex gap-2 flex-wrap mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`flex h-8 items-center justify-center gap-x-2 rounded-lg px-3 ${
              filter === 'all'
                ? 'bg-primary/10 dark:bg-primary/20 text-primary dark:text-blue-300 font-semibold'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <p className="text-sm">All</p>
          </button>
          <button
            onClick={() => setFilter('page')}
            className={`flex h-8 items-center justify-center gap-x-2 rounded-lg pl-3 pr-2 ${
              filter === 'page'
                ? 'bg-primary/10 dark:bg-primary/20 text-primary dark:text-blue-300 font-semibold'
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
                ? 'bg-primary/10 dark:bg-primary/20 text-primary dark:text-blue-300 font-semibold'
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
