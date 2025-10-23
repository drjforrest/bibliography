'use client';

import type { Annotation } from '@/types';

interface AnnotationCardProps {
  annotation: Annotation;
}

export default function AnnotationCard({ annotation }: AnnotationCardProps) {
  const getBorderColor = () => {
    switch (annotation.type) {
      case 'highlight':
        return 'border-yellow-400';
      case 'underline':
        return 'border-green-500';
      case 'comment':
        return 'border-purple-500';
      default:
        return 'border-gray-400';
    }
  };

  const getQuoteBorderColor = () => {
    switch (annotation.type) {
      case 'highlight':
        return 'border-yellow-200 dark:border-yellow-800';
      case 'underline':
        return 'border-green-200 dark:border-green-800';
      case 'comment':
        return 'border-purple-200 dark:border-purple-800';
      default:
        return 'border-gray-200 dark:border-gray-800';
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className={`flex items-start gap-4 p-4 rounded-lg bg-white dark:bg-gray-800 shadow-sm border-l-4 ${getBorderColor()}`}>
      <img
        className="w-10 h-10 rounded-full mt-1"
        src={annotation.user.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(annotation.user.name)}`}
        alt={`${annotation.user.name} avatar`}
      />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-gray-800 dark:text-gray-200">{annotation.user.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{formatDate(annotation.createdAt)}</p>
        </div>

        {annotation.quote && (
          <blockquote className={`mt-1 border-l-2 ${getQuoteBorderColor()} pl-2 text-sm italic text-gray-600 dark:text-gray-400`}>
            &ldquo;{annotation.quote}&rdquo;
          </blockquote>
        )}

        {annotation.content && (
          <p className="font-body text-sm mt-2 text-gray-700 dark:text-gray-300">{annotation.content}</p>
        )}

        {annotation.page && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Page {annotation.page}</p>
        )}
      </div>
    </div>
  );
}
