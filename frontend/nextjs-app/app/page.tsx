'use client';

import { useState, useEffect } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import Sidebar from '@/components/layout/Sidebar';
import SearchBar from '@/components/library/SearchBar';
import ViewToggle from '@/components/library/ViewToggle';
import BookGrid from '@/components/library/BookGrid';
import type { Paper, ViewMode, SortOption, Topic } from '@/types';

// Mock data for development
const mockPapers: Paper[] = [
  {
    id: '1',
    title: 'The Pragmatic Programmer',
    authors: ['Andrew Hunt', 'David Thomas'],
    year: 1999,
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDKrJUbDwy6bfMq2zxhPjrGL5qtm8390pRj2yxjf8yKHMd5aspoH8ZFm4DthSk_Py_qIBrErhvbZQNcMBxPnb6v6l4_mwT98viXCu2_y1zmxUBre_yQXjgbu-cLyW7MMCjWHeZ_vd7JYN30Xzl3ByoyOMFM6Ll__4f10FcudRvvSbvNBq9hIUBCvKGJsJKhw41Bg4KjyIlrukEhUqD9W2oc6ssMv6GLsGJNF8AxZwapgyslFC2gWIVLjeKhpkG1zuPB-CyRG_ZVrkvP',
    addedAt: new Date(),
  },
  {
    id: '2',
    title: 'Clean Code',
    authors: ['Robert C. Martin'],
    year: 2008,
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDdsQSmHI3UOSMSN3TQCOxzdvGukNYNP0L8_RcX39wUZAimlaxJa9pd2q8AX8BCtrgg7unbG1DJMzELJPTlzC3FVOKfRXZ1WDzL9GNc1khkht_B3AuJEtvcegJWtPHn7yaHFfMOYnvbs7QCAmavIU_8Ra0Lp05BFkMUzI1fcccSjVsJMnGuvePw9UyoDhO-P1hU_isM95zDdU3xSUwfcuGR2019ywlBok1_xHGgPsv_hMEtS_CIscNaS6qa3POtn5mvHqGtYFh9xb0l',
    addedAt: new Date(),
  },
  {
    id: '3',
    title: 'Design Patterns',
    authors: ['Erich Gamma', 'Richard Helm', 'Ralph Johnson', 'John Vlissides'],
    year: 1994,
    coverImage: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAlzMhM8rt50pxy1-xp1cs9XJKZOEQ_lRtpI6-9zBiixsMw4B6vmvsYG3HABYrwLq4eyX_QvvlnImQGn_W4lLcdbO8XQ44_MuM4lIvJ7QNO4RIINFuIxBR9x4lOS8fTooLQ-vED8AcNjtRyiHp93aXialj5POCeehd8ul_tJm_xjrwORvwgQQ6uDQs6RAvrSq_0gEROXUTW9K_KUB7gf1BCLQuBFQ0bzeOj3vUZqwLK90mqvfmRyhXDCMLLySEbsQPOpK1M5z3qGttF',
    addedAt: new Date(),
  },
];

const mockTopics: Topic[] = [
  {
    id: '1',
    name: 'Computer Science',
    children: [
      { id: '1-1', name: 'Machine Learning' },
      { id: '1-2', name: 'Cybersecurity' },
    ],
  },
  {
    id: '2',
    name: 'History',
    children: [
      { id: '2-1', name: 'Ancient Rome' },
      { id: '2-2', name: 'World War II' },
    ],
  },
  {
    id: '3',
    name: 'Physics',
    children: [
      { id: '3-1', name: 'Quantum Mechanics' },
      { id: '3-2', name: 'Astrophysics' },
    ],
  },
];

export default function HomePage() {
  const [papers, setPapers] = useState<Paper[]>(mockPapers);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortOption>('date');
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // In production, this would call the API
    // For now, just filter mock data
    if (query) {
      const filtered = mockPapers.filter(
        (paper) =>
          paper.title.toLowerCase().includes(query.toLowerCase()) ||
          paper.authors.some((author) => author.toLowerCase().includes(query.toLowerCase()))
      );
      setPapers(filtered);
    } else {
      setPapers(mockPapers);
    }
  };

  const handleSort = (option: SortOption) => {
    setSortBy(option);
    const sorted = [...papers].sort((a, b) => {
      switch (option) {
        case 'title':
          return a.title.localeCompare(b.title);
        case 'author':
          return a.authors[0].localeCompare(b.authors[0]);
        case 'date':
        default:
          return b.addedAt.getTime() - a.addedAt.getTime();
      }
    });
    setPapers(sorted);
  };

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-background-light dark:bg-background-dark">
        <Sidebar topics={mockTopics} />

        <main className="flex-1 p-6">
          <div className="flex flex-col h-full">
            {/* Search and View Toggle */}
            <div className="flex items-center justify-between mb-6 gap-4">
              <SearchBar onSearch={handleSearch} />
              <div className="flex items-center gap-4">
                <ViewToggle view={viewMode} onViewChange={setViewMode} />
              </div>
            </div>

            {/* Sort Options */}
            <div className="flex gap-3 pb-4 flex-wrap">
              <button
                onClick={() => handleSort('date')}
                className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                  sortBy === 'date'
                    ? 'bg-primary text-white'
                    : 'bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                <p className="text-sm font-medium leading-normal">Sort by Date</p>
                <span className="material-symbols-outlined text-base">arrow_drop_down</span>
              </button>
              <button
                onClick={() => handleSort('title')}
                className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                  sortBy === 'title'
                    ? 'bg-primary text-white'
                    : 'bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                <p className="text-sm font-medium leading-normal">Sort by Title</p>
                <span className="material-symbols-outlined text-base">arrow_drop_down</span>
              </button>
              <button
                onClick={() => handleSort('author')}
                className={`flex h-8 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-2 ${
                  sortBy === 'author'
                    ? 'bg-primary text-white'
                    : 'bg-gray-200 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                <p className="text-sm font-medium leading-normal">Sort by Author</p>
                <span className="material-symbols-outlined text-base">arrow_drop_down</span>
              </button>
            </div>

            {/* Papers Grid/List */}
            <div className="flex-1 overflow-y-auto">
              <BookGrid papers={papers} view={viewMode} />
            </div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
