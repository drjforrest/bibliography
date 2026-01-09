'use client';

import { useApi } from '@/lib/api';
import { useEffect, useState } from 'react';

interface Author {
  authorId?: string;
  name: string;
}

interface OpenAccessPdf {
  url?: string;
  status?: string;
}

interface RecommendedPaper {
  paperId: string;
  title: string;
  url?: string;
  abstract?: string;
  year?: number;
  authors?: Author[];
  citationCount?: number;
  isOpenAccess?: boolean;
  openAccessPdf?: OpenAccessPdf;
}

interface RecommendationsModalProps {
  paperId: number;
  paperTitle: string;
  onClose: () => void;
}

export function RecommendationsModal({
  paperId,
  paperTitle,
  onClose,
}: RecommendationsModalProps) {
  const [loading, setLoading] = useState(true);
  const [recommendations, setRecommendations] = useState<RecommendedPaper[]>([]);
  const [error, setError] = useState<string | null>(null);
  const api = useApi();

  useEffect(() => {
    loadRecommendations();
  }, [paperId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadRecommendations() {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRecommendations(paperId);
      setRecommendations(data.recommendations);


    } catch (err: any) {
      console.error('Failed to load recommendations:', err);
      setError(err?.message || 'Failed to load recommendations. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const handleAddToLibrary = () => {
    // Placeholder for future implementation
    alert('Paper import feature will be available soon!');
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <span className="material-symbols-outlined text-[24px]">
                auto_awesome
              </span>
              Related Papers
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Based on: {paperTitle}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <span className="material-symbols-outlined text-[24px]">
              close
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#4e989e]"></div>
              <p className="ml-3 text-gray-600 dark:text-gray-400">Loading recommendations...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <span className="material-symbols-outlined text-[48px] text-gray-400 mb-4">
                error_outline
              </span>
              <p className="text-gray-600 dark:text-gray-400">{error}</p>
            </div>
          ) : recommendations.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No recommendations found for this paper.
            </div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((paper, idx) => (
                <RecommendationCard
                  key={paper.paperId}
                  paper={paper}
                  rank={idx + 1}
                  onAddToLibrary={handleAddToLibrary}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

interface RecommendationCardProps {
  paper: RecommendedPaper;
  rank: number;
  onAddToLibrary: () => void;
}

function RecommendationCard({ paper, rank, onAddToLibrary }: RecommendationCardProps) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3 hover:shadow-md transition-shadow bg-white dark:bg-gray-800">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-gray-500 dark:text-gray-400">
              #{rank}
            </span>
            <h3 className="font-semibold leading-tight text-gray-900 dark:text-gray-100">
              {paper.title}
            </h3>
          </div>

          {paper.authors && paper.authors.length > 0 && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {paper.authors
                .slice(0, 3)
                .map((a) => a.name)
                .join(', ')}
              {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
            </p>
          )}

          {paper.abstract && (
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
              {paper.abstract}
            </p>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            {paper.year && (
              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                {paper.year}
              </span>
            )}
            {paper.citationCount !== undefined && (
              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                {paper.citationCount} citations
              </span>
            )}
            {paper.isOpenAccess && (
              <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                Open Access
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          {paper.url && (
            <a
              href={paper.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="Open in Semantic Scholar"
            >
              <span className="material-symbols-outlined text-[20px] text-gray-600 dark:text-gray-400">
                open_in_new
              </span>
            </a>
          )}

          {paper.openAccessPdf?.url && (
            <a
              href={paper.openAccessPdf.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="Download PDF"
            >
              <span className="material-symbols-outlined text-[20px] text-gray-600 dark:text-gray-400">
                download
              </span>
            </a>
          )}

          <button
            onClick={onAddToLibrary}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            title="Add to library (coming soon)"
          >
            <span className="material-symbols-outlined text-[20px] text-gray-600 dark:text-gray-400">
              bookmark_add
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}
