'use client';

import type { Paper } from '@/types';
import { LITERATURE_TYPE_LABELS, LITERATURE_TYPE_COLORS } from '@/types';
import Link from 'next/link';
import { useState } from 'react';

interface BookCardProps {
  paper: Paper;
  onChatWithDocument?: (documentId: number) => void;
}

export default function BookCard({ paper, onChatWithDocument }: BookCardProps) {
  const [imageError, setImageError] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Generate thumbnail URL if paper has an ID
  const thumbnailUrl = paper.id
    ? `${API_URL}/api/v1/papers/${paper.id}/thumbnail`
    : null;

  // Determine background image source
  const getBackgroundImage = () => {
    if (paper.coverImage) {
      return `url(${paper.coverImage})`;
    }
    if (thumbnailUrl && !imageError) {
      return `url(${thumbnailUrl})`;
    }
    return 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
  };

  const showFallbackText = !paper.coverImage && (!thumbnailUrl || imageError);

  return (
    <div className="group relative">
      <Link href={`/papers/${paper.id}`} className="flex flex-col gap-3">
        <div
          className="w-full bg-center bg-no-repeat aspect-[3/4] bg-cover rounded-lg shadow-md group-hover:shadow-xl transition-shadow cursor-pointer relative"
          style={{
            backgroundImage: getBackgroundImage(),
          }}
          title={paper.title}
        >
          {/* Literature Type Badge */}
          {paper.literature_type && paper.literature_type !== 'PEER_REVIEWED' && (
            <div className="absolute top-2 left-2 z-10">
              <span className={`px-2 py-1 text-xs font-semibold rounded ${LITERATURE_TYPE_COLORS[paper.literature_type]}`}>
                {LITERATURE_TYPE_LABELS[paper.literature_type]}
              </span>
            </div>
          )}

          {/* Hidden image to detect loading errors */}
          {thumbnailUrl && !imageError && (
            <img
              src={thumbnailUrl}
              alt=""
              className="hidden"
              onError={() => setImageError(true)}
            />
          )}

          {showFallbackText && (
            <div className="w-full h-full flex items-center justify-center p-4">
              <span className="text-white text-center font-medium line-clamp-4">{paper.title}</span>
            </div>
          )}
        </div>
        <div>
          <p className="text-base font-medium leading-normal text-gray-900 dark:text-white truncate">
            {paper.title}
          </p>
          <p className="text-sm font-normal leading-normal text-gray-500 dark:text-gray-400 truncate">
            {paper.authors.join(', ')}
          </p>
          {paper.year && (
            <p className="text-xs text-gray-400 dark:text-gray-500">{paper.year}</p>
          )}
        </div>
      </Link>

      {/* Chat button overlay */}
      {onChatWithDocument && (
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onChatWithDocument(paper.id);
          }}
          className="absolute top-2 right-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-2 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity"
          title="Chat with this document"
        >
          <span className="material-symbols-outlined text-sm">chat</span>
        </button>
      )}
    </div>
  );
}
