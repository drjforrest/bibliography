'use client';

interface ActionButtonProps {
  onClick: () => void;
  className?: string;
  variant?: 'default' | 'floating' | 'minimal';
  label?: string;
}

/**
 * Action Button Component
 * 
 * Trigger button for opening the Paper Action Panel.
 * Can be used in different contexts:
 * - Library cards (floating on hover)
 * - Paper detail page (in header/toolbar)
 * - Future: selection mode for batch operations
 */
export default function ActionButton({
  onClick,
  className = '',
  variant = 'default',
  label = 'Actions',
}: ActionButtonProps) {
  const baseClasses = 'flex items-center gap-2 transition-all';

  const variantClasses = {
    default: 'px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700',
    floating: 'p-2 bg-white dark:bg-gray-800 rounded-full shadow-lg hover:shadow-xl border border-gray-200 dark:border-gray-700',
    minimal: 'p-1 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100',
  };

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      aria-label={label}
      title={label}
    >
      <span className="material-symbols-outlined text-[18px]">
        more_vert
      </span>
      {variant !== 'floating' && variant !== 'minimal' && (
        <span>{label}</span>
      )}
    </button>
  );
}
