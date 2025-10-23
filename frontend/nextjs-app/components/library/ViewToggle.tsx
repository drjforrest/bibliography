'use client';

import type { ViewMode } from '@/types';

interface ViewToggleProps {
  view: ViewMode;
  onViewChange: (view: ViewMode) => void;
}

export default function ViewToggle({ view, onViewChange }: ViewToggleProps) {
  return (
    <div className="flex h-10 items-center justify-center rounded-lg bg-gray-200 dark:bg-gray-800/50 p-1">
      <label
        className={`flex cursor-pointer h-full grow items-center justify-center overflow-hidden rounded-lg px-3 ${
          view === 'grid'
            ? 'bg-white dark:bg-gray-900/80 shadow-sm text-primary dark:text-white'
            : 'text-gray-500 dark:text-gray-400'
        } text-sm font-medium leading-normal`}
      >
        <span className="material-symbols-outlined">grid_view</span>
        <input
          type="radio"
          name="view-toggle"
          value="grid"
          checked={view === 'grid'}
          onChange={() => onViewChange('grid')}
          className="invisible w-0"
        />
      </label>

      <label
        className={`flex cursor-pointer h-full grow items-center justify-center overflow-hidden rounded-lg px-3 ${
          view === 'list'
            ? 'bg-white dark:bg-gray-900/80 shadow-sm text-primary dark:text-white'
            : 'text-gray-500 dark:text-gray-400'
        } text-sm font-medium leading-normal`}
      >
        <span className="material-symbols-outlined">view_list</span>
        <input
          type="radio"
          name="view-toggle"
          value="list"
          checked={view === 'list'}
          onChange={() => onViewChange('list')}
          className="invisible w-0"
        />
      </label>
    </div>
  );
}
