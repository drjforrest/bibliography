'use client';

import { LiteratureType, LITERATURE_TYPE_LABELS } from '@/types';

interface LiteratureTypeFilterProps {
  selectedType: LiteratureType | 'ALL';
  onTypeChange: (type: LiteratureType | 'ALL') => void;
}

export default function LiteratureTypeFilter({ selectedType, onTypeChange }: LiteratureTypeFilterProps) {
  const types: Array<LiteratureType | 'ALL'> = ['ALL', 'PEER_REVIEWED', 'GREY_LITERATURE', 'NEWS'];
  
  const getLabel = (type: LiteratureType | 'ALL'): string => {
    if (type === 'ALL') return 'All Types';
    return LITERATURE_TYPE_LABELS[type];
  };

  const getButtonClasses = (type: LiteratureType | 'ALL'): string => {
    const baseClasses = 'px-4 py-2 text-sm font-medium rounded-lg transition-colors';
    const isSelected = selectedType === type;
    
    if (isSelected) {
      return `${baseClasses} bg-blue-600 text-white`;
    }
    return `${baseClasses} bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600`;
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">
        Literature Type:
      </span>
      {types.map((type) => (
        <button
          key={type}
          onClick={() => onTypeChange(type)}
          className={getButtonClasses(type)}
        >
          {getLabel(type)}
        </button>
      ))}
    </div>
  );
}
