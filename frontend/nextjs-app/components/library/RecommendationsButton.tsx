'use client';

import { useState } from 'react';
import { RecommendationsModal } from './RecommendationsModal';

interface RecommendationsButtonProps {
  paperId: number;
  paperTitle: string;
}

export function RecommendationsButton({
  paperId,
  paperTitle,
}: RecommendationsButtonProps) {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <span className="material-symbols-outlined text-[18px]">
          auto_awesome
        </span>
        Find Related Papers
      </button>

      {showModal && (
        <RecommendationsModal
          paperId={paperId}
          paperTitle={paperTitle}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
