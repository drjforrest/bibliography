'use client';

import type { MessageTopic } from '@/types';
import { useState } from 'react';
import ContextMenu, { ContextMenuItem } from '@/components/shared/ContextMenu';

interface TopicListProps {
  topics: MessageTopic[];
  currentTopicId: number | null;
  onTopicSelect?: (topicId: number) => void;
  onRenameTopic?: (topicId: number, newName: string) => void;
  onDeleteTopic?: (topicId: number) => void;
}

export default function TopicList({
  topics,
  currentTopicId,
  onTopicSelect,
  onRenameTopic,
  onDeleteTopic
}: TopicListProps) {
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    topicId: number;
  } | null>(null);

  const handleContextMenu = (e: React.MouseEvent, topicId: number) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      topicId,
    });
  };

  const handleRename = (topicId: number) => {
    const topic = topics.find(t => t.id === topicId);
    if (!topic || !onRenameTopic) return;

    const newName = window.prompt('Rename topic:', topic.name);
    if (newName && newName.trim() && newName !== topic.name) {
      onRenameTopic(topicId, newName.trim());
    }
  };

  const handleDelete = (topicId: number) => {
    const topic = topics.find(t => t.id === topicId);
    if (!topic || !onDeleteTopic) return;

    if (window.confirm(`Are you sure you want to delete "${topic.name}" and all its messages?`)) {
      onDeleteTopic(topicId);
    }
  };

  const getContextMenuItems = (topicId: number): ContextMenuItem[] => [
    {
      label: 'Rename',
      icon: 'edit',
      onClick: () => handleRename(topicId),
    },
    {
      label: 'Delete',
      icon: 'delete',
      onClick: () => handleDelete(topicId),
      danger: true,
    },
  ];

  return (
    <>
      <nav className="flex flex-col gap-2">
        {topics.map((topic) => (
          <div
            key={topic.id}
            onClick={() => onTopicSelect?.(topic.id)}
            onContextMenu={(e) => handleContextMenu(e, topic.id)}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg cursor-pointer ${
              currentTopicId === topic.id
                ? 'bg-secondary dark:bg-gray-700'
                : 'hover:bg-secondary dark:hover:bg-gray-700'
            }`}
          >
            <span
              className={`material-symbols-outlined ${
                currentTopicId === topic.id
                  ? 'text-primary dark:text-accent'
                  : 'text-text-primary dark:text-gray-300'
              }`}
            >
              {topic.icon}
            </span>
            <p
              className={`text-sm font-medium flex-1 ${
                currentTopicId === topic.id
                  ? 'text-primary dark:text-white'
                  : 'text-text-primary dark:text-gray-300'
              }`}
            >
              {topic.name}
            </p>
            {topic.unread_count && topic.unread_count > 0 && (
              <span className="w-2 h-2 bg-accent rounded-full" />
            )}
          </div>
        ))}
      </nav>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={getContextMenuItems(contextMenu.topicId)}
          onClose={() => setContextMenu(null)}
        />
      )}
    </>
  );
}
