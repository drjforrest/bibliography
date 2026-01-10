'use client';

import { useApi } from '@/lib/api';
import type { Paper } from '@/types';
import type { ActionCategory, PaperAction } from '@/types/actions';
import { actionDefinitions, categoryMetadata } from '@/types/actions';
import { useEffect, useMemo, useState } from 'react';
import ActionCategoryComponent from './ActionCategory';

interface PaperActionPanelProps {
  paper: Paper;
  isOpen: boolean;
  onClose: () => void;
  onActionComplete?: (actionId: string) => void;
  // Future: support batch operations
  // papers?: Paper[];
}

export default function PaperActionPanel({
  paper,
  isOpen,
  onClose,
  onActionComplete,
}: PaperActionPanelProps) {
  const api = useApi();
  const [actionStates, setActionStates] = useState<Record<string, { status?: PaperAction['status'] }>>({});
  const [isFavorited, setIsFavorited] = useState(false);

  // Check favorite status
  useEffect(() => {
    if (isOpen && paper) {
      api.isFavorited(paper.id)
        .then(result => setIsFavorited(result.is_favorited))
        .catch(() => setIsFavorited(false));
    }
  }, [isOpen, paper, api]);

  // Group actions by category
  const actionsByCategory = useMemo(() => {
    const actions: PaperAction[] = [
      // Find Related Papers
      {
        ...actionDefinitions['find-related']!,
        onClick: async (paperIds: number[]) => {
          // Trigger recommendations - parent will handle opening modal
          onActionComplete?.('find-related');
          onClose();
        },
      },
      // Chat with PDF
      {
        ...actionDefinitions['chat-with-pdf']!,
        onClick: async (paperIds: number[]) => {
          // Navigate to chat - parent component will handle
          onActionComplete?.('chat-with-pdf');
          onClose();
        },
      },
      // Manage Tags
      {
        ...actionDefinitions['manage-tags']!,
        onClick: async (paperIds: number[]) => {
          // Parent component will handle tag dialog
          onActionComplete?.('manage-tags');
          onClose();
        },
      },
      // Toggle Favorite
      {
        ...actionDefinitions['toggle-favorite']!,
        title: isFavorited ? 'Remove from Favorites' : 'Add to Favorites',
        icon: isFavorited ? 'star' : 'star_outline',
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'processing' } }));
            if (isFavorited) {
              await api.removeFavorite(paperId);
            } else {
              await api.addFavorite(paperId);
            }
            setIsFavorited(prev => !prev);
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'completed' } }));
            // Remove the completed status after 2 seconds
            setTimeout(() => {
              setActionStates(prev => {
                // Safely remove 'toggle-favorite' while keeping other states
                const { ['toggle-favorite']: _removed, ...rest } = prev;
                return rest;
              });
            }, 2000);
            onActionComplete?.('toggle-favorite');
          } catch (error) {
            console.error('Failed to toggle favorite:', error);
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'error' } }));
          }
        },
        status: actionStates['toggle-favorite']?.status,
      },
      // Delete
      {
        ...actionDefinitions['delete']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          if (!confirm(`Are you sure you want to delete "${paper.title}"?`)) {
            return;
          }
          try {
            setActionStates(prev => ({ ...prev, 'delete': { status: 'processing' } }));
            await api.deletePaper(paperId);
            setActionStates(prev => ({ ...prev, 'delete': { status: 'completed' } }));
            onActionComplete?.('delete');
            // Parent will handle navigation/refresh
          } catch (error) {
            console.error('Failed to delete paper:', error);
            setActionStates(prev => ({ ...prev, 'delete': { status: 'error' } }));
            alert('Failed to delete paper. Please try again.');
          }
        },
        status: actionStates['delete']?.status,
      },
    ];

    // Group by category
    const grouped: Record<ActionCategory, PaperAction[]> = {
      'ai-powered': [],
      'organize': [],
      'share-export': [],
      'content': [],
      'manage': [],
    };

    actions.forEach(action => {
      grouped[action.category].push(action);
    });

    return grouped;
  }, [paper, isFavorited, api, actionStates, onActionComplete, onClose]);

  // Keyboard shortcuts
  useEffect(() => {
    if (typeof isOpen === 'undefined' || !isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Close on Escape
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Action shortcuts (when panel is open)
      // R - Find Related
      if (e.key === 'r' || e.key === 'R') {
        const action = actionsByCategory['ai-powered'].find(a => a.id === 'find-related');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // C - Chat
      if (e.key === 'c' || e.key === 'C') {
        const action = actionsByCategory['content'].find(a => a.id === 'chat-with-pdf');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // T - Tags
      if (e.key === 't' || e.key === 'T') {
        const action = actionsByCategory['organize'].find(a => a.id === 'manage-tags');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // F - Favorite
      if (e.key === 'f' || e.key === 'F') {
        const action = actionsByCategory['organize'].find(a => a.id === 'toggle-favorite');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, actionsByCategory, onClose, paper.id]);

  if (!isOpen) return null;

  // Sort categories by order
  const sortedCategories = (Object.keys(categoryMetadata) as ActionCategory[]).sort(
    (a, b) => categoryMetadata[a].order - categoryMetadata[b].order
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={`
          fixed right-0 top-0 bottom-0 w-full max-w-md
          bg-white dark:bg-gray-800
          shadow-2xl z-50
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
          flex flex-col
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Paper Actions
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">
              {paper.title}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            aria-label="Close panel"
          >
            <span className="material-symbols-outlined text-[24px] text-gray-600 dark:text-gray-400">
              close
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {sortedCategories.map((category) => {
            const actions = actionsByCategory[category];
            if (actions.length === 0) return null;

            return (
              <ActionCategoryComponent
                key={category}
                category={category}
                actions={actions}
                paperCount={1} // Currently single paper, will support batch later
                defaultExpanded={category === 'ai-powered' || category === 'organize'}
              />
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
          <p>Press <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">Esc</kbd> to close</p>
        </div>
      </div>
    </>
  );
}
