'use client';

import type { PaperAction, ActionBadge } from '@/types/actions';

interface ActionCardProps {
  action: PaperAction;
  isSelected?: boolean;
  paperCount?: number; // For future batch support (default: 1)
}

export default function ActionCard({ action, isSelected = false, paperCount = 1 }: ActionCardProps) {
  const isBatch = paperCount > 1;
  const displayTitle = isBatch && action.batchLabel ? action.batchLabel : action.title;
  const disabled = action.disabled || action.status === 'disabled' || action.status === 'processing';

  const getStatusColor = () => {
    switch (action.status) {
      case 'processing':
        return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
      case 'completed':
        return 'border-green-500 bg-green-50 dark:bg-green-900/20';
      case 'error':
        return 'border-red-500 bg-red-50 dark:bg-red-900/20';
      default:
        return 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800';
    }
  };

  const getBadgeColor = (badge?: ActionBadge) => {
    switch (badge) {
      case 'new':
        return 'bg-green-500 text-white';
      case 'pro':
        return 'bg-purple-500 text-white';
      case 'beta':
        return 'bg-orange-500 text-white';
      default:
        return '';
    }
  };

  return (
    <button
      onClick={() => !disabled && action.onClick([1])} // TODO: Replace with actual paper IDs
      disabled={disabled}
      className={`
        relative w-full p-4 rounded-lg border-2 transition-all
        ${disabled 
          ? 'opacity-50 cursor-not-allowed' 
          : 'cursor-pointer hover:shadow-md hover:border-[#4e989e] dark:hover:border-[#94d2bd]'
        }
        ${isSelected ? 'ring-2 ring-[#4e989e] ring-offset-2' : ''}
        ${getStatusColor()}
      `}
    >
      {/* Badge */}
      {action.badge && (
        <div className={`
          absolute top-2 right-2 px-2 py-0.5 text-xs font-semibold rounded
          ${getBadgeColor(action.badge)}
        `}>
          {action.badge.toUpperCase()}
        </div>
      )}

      {/* Icon */}
      <div className="flex items-start gap-3 mb-2">
        <span className="material-symbols-outlined text-[32px] text-[#4e989e] dark:text-[#94d2bd]">
          {action.icon}
        </span>
        <div className="flex-1 text-left">
          {/* Title */}
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
            {displayTitle}
            {isBatch && paperCount > 1 && (
              <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                ({paperCount} papers)
              </span>
            )}
          </h3>
          
          {/* Description */}
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {action.description}
          </p>
        </div>
      </div>

      {/* Status Indicator */}
      {action.status === 'processing' && (
        <div className="absolute bottom-2 left-4 flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400">
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 dark:border-blue-400"></div>
          Processing...
        </div>
      )}

      {action.status === 'completed' && (
        <div className="absolute bottom-2 left-4 flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
          <span className="material-symbols-outlined text-[16px]">check_circle</span>
          Completed
        </div>
      )}

      {/* Keyboard Shortcut Hint */}
      {action.keyboardShortcut && !disabled && (
        <div className="absolute bottom-2 right-2">
          <kbd className="px-2 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
            {action.keyboardShortcut}
          </kbd>
        </div>
      )}
    </button>
  );
}
