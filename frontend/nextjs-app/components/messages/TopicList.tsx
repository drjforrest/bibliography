'use client';

import type { MessageTopic } from '@/types';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface TopicListProps {
  topics: MessageTopic[];
  onTopicSelect?: (topicId: string) => void;
}

export default function TopicList({ topics, onTopicSelect }: TopicListProps) {
  const pathname = usePathname();

  const isActive = (topicId: string) => pathname === `/messages/${topicId}`;

  const handleTopicClick = (topicId: string) => {
    if (onTopicSelect) {
      onTopicSelect(topicId);
    }
  };

  return (
    <nav className="flex flex-col gap-2">
      {topics.map((topic) => (
        <Link
          key={topic.id}
          href={`/messages/${topic.id}`}
          onClick={() => handleTopicClick(topic.id)}
          className={`flex items-center gap-3 px-4 py-2.5 rounded-lg ${
            isActive(topic.id)
              ? 'bg-secondary dark:bg-gray-700'
              : 'hover:bg-secondary dark:hover:bg-gray-700'
          }`}
        >
          <span
            className={`material-symbols-outlined ${
              isActive(topic.id)
                ? 'text-primary dark:text-accent'
                : 'text-text-primary dark:text-gray-300'
            }`}
          >
            {topic.icon}
          </span>
          <p
            className={`text-sm font-medium flex-1 ${
              isActive(topic.id)
                ? 'text-primary dark:text-white'
                : 'text-text-primary dark:text-gray-300'
            }`}
          >
            {topic.name}
          </p>
          {topic.unreadCount && topic.unreadCount > 0 && (
            <span className="w-2 h-2 bg-accent rounded-full" />
          )}
        </Link>
      ))}
    </nav>
  );
}
