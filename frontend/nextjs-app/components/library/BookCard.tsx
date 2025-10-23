'use client';

import Link from 'next/link';
import type { Paper } from '@/types';

interface BookCardProps {
  paper: Paper;
}

export default function BookCard({ paper }: BookCardProps) {
  return (
    <Link href={`/papers/${paper.id}`} className="flex flex-col gap-3 group">
      <div
        className="w-full bg-center bg-no-repeat aspect-[3/4] bg-cover rounded-lg shadow-md group-hover:shadow-xl transition-shadow cursor-pointer"
        style={{
          backgroundImage: paper.coverImage
            ? `url(${paper.coverImage})`
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
        title={paper.title}
      >
        {!paper.coverImage && (
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
  );
}
