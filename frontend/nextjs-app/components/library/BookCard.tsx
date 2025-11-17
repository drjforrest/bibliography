'use client';

import TagDialog from '@/components/library/TagDialog';
import ContextMenu, { ContextMenuItem } from '@/components/shared/ContextMenu';
import { api } from '@/lib/api';
import type { Paper } from '@/types';
import { LITERATURE_TYPE_COLORS, LITERATURE_TYPE_LABELS } from '@/types';
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
  const [isTogglingFavorite, setIsTogglingFavorite] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [showTagDialog, setShowTagDialog] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Check if paper is favorited on mount
  useEffect(() => {
    const checkFavorited = async () => {
      try {
        const result = await api.isFavorited(paper.id);
        setIsFavorited(result.is_favorited);
      } catch (error) {
        console.error('Failed to check favorite status:', error);
      }
    };
    checkFavorited();
  }, [paper.id]);

  const handleToggleFavorite = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (isTogglingFavorite) return;

    setIsTogglingFavorite(true);
    try {
      if (isFavorited) {
        await api.removeFavorite(paper.id);
        setIsFavorited(false);
      } else {
        await api.addFavorite(paper.id);
        setIsFavorited(true);
      }
      // Notify parent component of change
      onFavoriteChange?.();
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    } finally {
      setIsTogglingFavorite(false);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
    });
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${paper.title}"?`)) return;

    try {
      await api.deletePaper(paper.id);
      onDelete?.();
    } catch (error) {
      console.error('Failed to delete paper:', error);
      alert('Failed to delete paper. Please try again.');
    }
  };

  const contextMenuItems: ContextMenuItem[] = [
    {
      label: 'Chat with PDF',
      icon: 'chat',
      onClick: () => onChatWithDocument?.(paper.id),
    },
    {
      label: 'Manage Tags',
      icon: 'tag',
      onClick: () => setShowTagDialog(true),
    },
    {
      label: isFavorited ? 'Remove from Favorites' : 'Add to Favorites',
      icon: isFavorited ? 'star' : 'star_outline',
      onClick: (e?: any) => handleToggleFavorite(e || {} as React.MouseEvent),
    },
    {
      label: 'Delete',
      icon: 'delete',
      onClick: handleDelete,
      danger: true,
    },
  ];

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
    <div className="group relative" onContextMenu={handleContextMenu}>
      <Link href={`/papers/${paper.id}`} className="flex flex-col gap-3">
        <div
          className="w-full bg-center bg-no-repeat aspect-[3/4] bg-cover rounded-lg shadow-md group-hover:shadow-xl transition-shadow cursor-pointer relative"
          style={{
            backgroundImage: getBackgroundImage(),
          }}
          title={`${paper.title}\n\n${paper.summary || 'No summary available'}`}
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


      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenuItems}
          onClose={() => setContextMenu(null)}
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
