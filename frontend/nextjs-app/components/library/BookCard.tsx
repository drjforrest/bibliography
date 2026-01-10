'use client';

import ActionButton from '@/components/library/ActionButton';
import PaperActionPanel from '@/components/library/PaperActionPanel';
import TagDialog from '@/components/library/TagDialog';
import { getApiBaseUrl, useApi } from '@/lib/api';
import type { Paper } from '@/types';
import { LITERATURE_TYPE_COLORS, LITERATURE_TYPE_LABELS } from '@/types';
import { useAuth } from '@clerk/nextjs';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import Link from 'next/link';
import { useEffect, useState } from 'react';

interface BookCardProps {
  paper: Paper;
  onChatWithDocument?: (documentId: number) => void;
  onFavoriteChange?: () => void;
  onTagChange?: () => void;
  onDelete?: () => void;
}

export default function BookCard({ paper, onChatWithDocument, onFavoriteChange, onTagChange, onDelete }: BookCardProps) {
  const [imageError, setImageError] = useState(false);
  const [isFavorited, setIsFavorited] = useState(false);
  const [showActionPanel, setShowActionPanel] = useState(false);
  const [showTagDialog, setShowTagDialog] = useState(false);
  const { isLoaded, isSignedIn } = useAuth();
  const api = useApi();

  // Make card draggable
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `paper-${paper.id}`,
    data: {
      type: 'paper',
      paper: paper,
      literature_type: paper.literature_type || 'PEER_REVIEWED', // Include literature_type in drag data
    },
    disabled: !isLoaded || !isSignedIn, // Only allow dragging when authenticated
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
    cursor: isDragging ? 'grabbing' : 'grab',
  };

  // Reset image error state when paper changes
  useEffect(() => {
    setImageError(false);
  }, [paper.id]);

  // Check if paper is favorited on mount (only when authenticated)
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    
    const checkFavorited = async () => {
      try {
        const result = await api.isFavorited(paper.id);
        setIsFavorited(result.is_favorited);
      } catch (error) {
        // Silently fail - user might not be authenticated or paper might not exist
        // Don't spam console with errors
      }
    };
    checkFavorited();
  }, [paper.id, isLoaded, isSignedIn, api]);

  const handleActionComplete = (actionId: string) => {
    switch (actionId) {
      case 'chat-with-pdf':
        onChatWithDocument?.(paper.id);
        break;
      case 'manage-tags':
        setShowTagDialog(true);
        break;
      case 'toggle-favorite':
        onFavoriteChange?.();
        break;
      case 'delete':
        onDelete?.();
        break;
      case 'find-related':
        // Recommendations handled by panel itself
        break;
    }
  };

  // Generate thumbnail URL if paper has an ID
  // Use full API URL in production (client-side image requests don't use Next.js rewrites)
  const thumbnailUrl = paper.id
    ? `${getApiBaseUrl()}/api/v1/papers/${paper.id}/thumbnail`
    : null;

  // Determine background image source
  const getBackgroundImage = () => {
    if (paper.coverImage) {
      return `url(${paper.coverImage})`;
    }
    if (thumbnailUrl && !imageError) {
      return `url(${thumbnailUrl})`;
    }
    return 'linear-gradient(135deg, #4e989e 0%, #94d2bd 100%)';
  };

  const showFallbackText = !paper.coverImage && (!thumbnailUrl || imageError);

  return (
    <div 
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="group relative"
    >
      <Link 
        href={`/papers/${paper.id}`} 
        className="flex flex-col gap-3"
        onClick={(e) => {
          // Prevent navigation if currently dragging
          if (isDragging) {
            e.preventDefault();
          }
        }}
      >
        <div
          className="w-full bg-center bg-no-repeat aspect-[3/4] bg-cover rounded-lg shadow-md group-hover:shadow-xl transition-shadow cursor-pointer relative"
          style={{
            backgroundImage: getBackgroundImage(),
          }}
          title={`${paper.title}\n\n${paper.short_description || paper.summary || 'No summary available'}`}
        >
          {/* Action Button - Appears on Hover */}
          {isLoaded && isSignedIn && (
            <div 
              className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-20"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
              }}
            >
              <ActionButton
                onClick={() => setShowActionPanel(true)}
                variant="floating"
              />
            </div>
          )}
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
              onError={(e) => {
                // Silently handle missing thumbnails - don't spam console
                setImageError(true);
              }}
              onLoad={() => {
                // Image loaded successfully - no need to log
              }}
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

      {/* Action Panel */}
      {showActionPanel && (
        <PaperActionPanel
          paper={paper}
          isOpen={showActionPanel}
          onClose={() => setShowActionPanel(false)}
          onActionComplete={handleActionComplete}
        />
      )}

      {/* Tag Dialog */}
      <TagDialog
        isOpen={showTagDialog}
        onClose={() => setShowTagDialog(false)}
        paper={paper}
        onTagChange={() => {
          onTagChange?.();
          setShowTagDialog(false);
        }}
      />
    </div>
  );
}
