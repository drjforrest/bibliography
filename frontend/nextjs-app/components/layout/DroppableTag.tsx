'use client';

import { useDroppable, useDndContext } from '@dnd-kit/core';
import type { Topic, LiteratureType } from '@/types';
import Link from 'next/link';
import { getTagColorClasses } from '@/lib/tagColors';

interface DroppableTagProps {
  topic: Topic;
  isChild?: boolean;
  dominantLiteratureType?: LiteratureType;
}

export default function DroppableTag({ topic, isChild = false, dominantLiteratureType }: DroppableTagProps) {
  const { active } = useDndContext();
  
  const { setNodeRef, isOver } = useDroppable({
    id: `tag-${topic.id}`,
  });

  // Get the dragged paper's literature_type from active drag
  const draggedPaperType = active?.data?.current?.literature_type as LiteratureType | undefined;
  
  // Check if the dragged paper's literature_type matches this tag's type
  // If tag has no dominant type yet (empty tag), allow any drop
  // If tag has a dominant type, only allow matching types
  const isValidDrop = !dominantLiteratureType || !draggedPaperType || draggedPaperType === dominantLiteratureType;

  // Get color classes based on literature type
  const colorClasses = getTagColorClasses(dominantLiteratureType);

  // Highlight when dragging over - different styles for valid vs invalid drops
  const dropZoneStyle = isOver
    ? isValidDrop
      ? {
          backgroundColor: 'rgba(78, 152, 158, 0.2)',
          border: '2px dashed #4e989e',
          borderRadius: '0.5rem',
        }
      : {
          backgroundColor: 'rgba(239, 68, 68, 0.2)',
          border: '2px dashed #ef4444',
          borderRadius: '0.5rem',
          opacity: 0.6,
        }
    : {};

  const baseClasses = isChild
    ? 'block text-sm rounded-lg px-3 py-2 transition-colors'
    : 'flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors';

  return (
    <li>
      <div
        ref={setNodeRef}
        style={dropZoneStyle}
        className={`${baseClasses} ${isOver ? '' : colorClasses} ${
          isChild
            ? 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800'
        }`}
      >
        <Link
          href={`/topics/${topic.id}`}
          className="flex-1 flex items-center gap-2"
          onClick={(e) => {
            // Prevent navigation if currently dragging over
            if (isOver) {
              e.preventDefault();
            }
          }}
        >
          <span>{topic.name}</span>
          {isOver && (
            <>
              {isValidDrop ? (
                <span className="material-symbols-outlined text-[#4e989e] text-sm" aria-label="Drop here">
                  add_circle
                </span>
              ) : (
                <span className="material-symbols-outlined text-red-500 text-sm" aria-label="Cannot drop - literature type mismatch">
                  cancel
                </span>
              )}
            </>
          )}
        </Link>
      </div>
      {topic.children && topic.children.length > 0 && (
        <ul className="pl-6 mt-1 space-y-1">
          {topic.children.map((child) => (
            <DroppableTag
              key={child.id}
              topic={child}
              isChild={true}
              dominantLiteratureType={child.dominantLiteratureType || dominantLiteratureType}
            />
          ))}
        </ul>
      )}
    </li>
  );
}
