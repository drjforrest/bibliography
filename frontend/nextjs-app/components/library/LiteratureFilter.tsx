'use client';

import { useState } from 'react';

export type LiteratureType = 'all' | 'peer-reviewed' | 'grey-literature' | 'news';

interface LiteratureFilterProps {
  onFilterChange: (type: LiteratureType) => void;
  currentFilter: LiteratureType;
}

const filters: { value: LiteratureType; label: string; icon: string; description: string }[] = [
  { 
    value: 'all', 
    label: 'All Literature', 
    icon: 'library_books',
    description: 'View all papers'
  },
  { 
    value: 'peer-reviewed', 
    label: 'Peer-Reviewed', 
    icon: 'verified',
    description: 'Academic journal articles'
  },
  { 
    value: 'grey-literature', 
    label: 'Grey Literature', 
    icon: 'description',
    description: 'Reports, white papers, working papers'
  },
  { 
    value: 'news', 
    label: 'News', 
    icon: 'newspaper',
    description: 'News articles and media'
  },
];

export default function LiteratureFilter({ onFilterChange, currentFilter }: LiteratureFilterProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {filters.map((filter) => (
        <button
          key={filter.value}
          onClick={() => onFilterChange(filter.value)}
          title={filter.description}
          className={`flex h-9 items-center justify-center gap-x-2 rounded-lg px-4 transition-colors ${
            currentFilter === filter.value
              ? 'bg-[#4e989e] text-white shadow-md'
              : 'bg-gray-100 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <span className="material-symbols-outlined text-base">
            {filter.icon}
          </span>
          <p className="text-sm font-medium leading-normal">
            {filter.label}
          </p>
        </button>
      ))}
    </div>
  );
}