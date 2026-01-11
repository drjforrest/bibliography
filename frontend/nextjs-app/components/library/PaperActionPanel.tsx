'use client';

import { useApi } from '@/lib/api';
import type { Paper } from '@/types';
import type { ActionCategory, PaperAction } from '@/types/actions';
import { actionDefinitions, categoryMetadata } from '@/types/actions';
import { useEffect, useMemo, useRef, useState } from 'react';

interface PaperActionPanelProps {
  paper: Paper;
  isOpen: boolean;
  onClose: () => void;
  onActionComplete?: (actionId: string) => void;
  buttonRef?: React.RefObject<HTMLButtonElement | HTMLDivElement>;
  // Future: support batch operations
  // papers?: Paper[];
}

export default function PaperActionPanel({
  paper,
  isOpen,
  onClose,
  onActionComplete,
  buttonRef,
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

  // Calculate position for dropdown (below action button, aligned to right)
  const [position, setPosition] = useState({ top: 0, right: 0 });
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && buttonRef?.current) {
      const button = buttonRef.current instanceof HTMLElement 
        ? buttonRef.current 
        : buttonRef.current.querySelector('button') || buttonRef.current;
      
      if (button) {
        const rect = button.getBoundingClientRect();
        setPosition({
          top: rect.bottom + 8, // 8px gap below button
          right: window.innerWidth - rect.right, // Align to right edge of button
        });
      }
    }
  }, [isOpen, buttonRef]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
      />

      {/* Floating Dropdown Menu */}
      <div
        ref={menuRef}
        className="fixed z-50 w-80 max-h-[calc(100vh-120px)] bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden"
        style={{ top: `${position.top}px`, right: `${position.right}px` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
              {paper.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="ml-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors shrink-0"
            aria-label="Close menu"
          >
            <span className="material-symbols-outlined text-lg text-gray-600 dark:text-gray-400">
              close
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-2">
          {sortedCategories.map((category) => {
            const actions = actionsByCategory[category];
            if (actions.length === 0) return null;

            return (
              <div key={category} className="mb-2 last:mb-0">
                <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {categoryMetadata[category].label}
                </div>
                <div className="space-y-0.5">
                  {actions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => {
                        action.onClick([paper.id]);
                      }}
                      disabled={action.disabled || action.status === 'processing'}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-sm text-left transition-colors ${
                        action.disabled || action.status === 'processing'
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <span className="material-symbols-outlined text-xl text-gray-600 dark:text-gray-400 shrink-0">
                        {action.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            {action.title}
                          </span>
                          {action.badge && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              action.badge === 'new' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' :
                              action.badge === 'beta' ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' :
                              'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                            }`}>
                              {action.badge}
                            </span>
                          )}
                        </div>
                        {action.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                            {action.description}
                          </p>
                        )}
                      </div>
                      {action.status === 'processing' && (
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-[#4e989e] shrink-0" />
                      )}
                      {action.status === 'completed' && (
                        <span className="material-symbols-outlined text-lg text-green-600 dark:text-green-400 shrink-0">
                          check_circle
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
