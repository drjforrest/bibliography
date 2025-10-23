"use client";

import type { Paper, ViewMode } from "@/types";
import BookCard from "./BookCard";

interface BookGridProps {
  papers: Paper[];
  view: ViewMode;
}

export default function BookGrid({ papers, view }: BookGridProps) {
  if (papers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <span className="material-symbols-outlined text-6xl text-gray-300 dark:text-gray-600 mb-4">
          library_books
        </span>
        <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
          No papers found
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Try adjusting your search or filters
        </p>
      </div>
    );
  }

  if (view === "list") {
    return (
      <div className="space-y-4">
        {papers.map((paper) => (
          <div
            key={paper.id}
            className="flex gap-4 p-4 bg-white dark:bg-gray-800/50 rounded-lg shadow hover:shadow-md transition-shadow"
          >
            <div
              className="w-24 h-32 bg-center bg-no-repeat bg-cover rounded flex-shrink-0"
              style={{
                backgroundImage: paper.coverImage
                  ? `url(${paper.coverImage})`
                  : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              }}
            />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                {paper.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                {paper.authors.join(", ")} {paper.year && `(${paper.year})`}
              </p>
              {paper.abstract && (
                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                  {paper.abstract}
                </p>
              )}
              {paper.tags && paper.tags.length > 0 && (
                <div className="flex gap-2 mt-2">
                  {paper.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="text-xs px-2 py-1 bg-primary/10 text-primary dark:bg-primary/20 dark:text-blue-300 rounded"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-6">
      {papers.map((paper) => (
        <BookCard key={paper.id} paper={paper} />
      ))}
    </div>
  );
}
