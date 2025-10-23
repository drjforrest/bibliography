'use client';

import type { Message } from '@/types';
import MessageCard from './MessageCard';

interface MessageThreadProps {
  messages: Message[];
  onReply?: (messageId: string) => void;
}

export default function MessageThread({ messages, onReply }: MessageThreadProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <span className="material-symbols-outlined text-6xl text-gray-300 dark:text-gray-600 mb-4">
          forum
        </span>
        <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
          No messages yet
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Be the first to start the conversation
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {messages.map((message) => (
        <div key={message.id}>
          <MessageCard message={message} onReply={onReply} />

          {/* Render replies */}
          {message.replies && message.replies.length > 0 && (
            <div className="mt-6 space-y-6">
              {message.replies.map((reply) => (
                <MessageCard key={reply.id} message={reply} isReply onReply={onReply} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
