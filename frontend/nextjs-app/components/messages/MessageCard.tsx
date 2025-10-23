"use client";

import type { Message } from "@/types";

interface MessageCardProps {
  message: Message;
  isReply?: boolean;
  onReply?: (messageId: string) => void;
}

export default function MessageCard({
  message,
  isReply = false,
  onReply,
}: MessageCardProps) {
  const formatDate = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) return "Just now";
    if (diffHours === 1) return "1 hour ago";
    if (diffHours < 24) return `${diffHours} hours ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "1 day ago";
    if (diffDays < 7) return `${diffDays} days ago`;

    return date.toLocaleDateString();
  };

  return (
    <div
      className={`flex w-full flex-row items-start justify-start gap-4 ${isReply ? "pl-16" : ""}`}
    >
      <div
        className="bg-center bg-no-repeat aspect-square bg-cover rounded-full w-11 shrink-0"
        style={{
          backgroundImage: message.user.avatar
            ? `url(${message.user.avatar})`
            : `url(https://ui-avatars.com/api/?name=${encodeURIComponent(message.user.name || "User")})`,
        }}
      />
      <div className="flex h-full flex-1 flex-col items-start justify-start">
        <div className="flex w-full flex-row items-center justify-start gap-x-3">
          <p className="text-base font-bold text-text-primary dark:text-white">
            {message.user.name || "Anonymous"}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {formatDate(message.createdAt)}
          </p>
        </div>
        <p className="text-base text-text-primary dark:text-gray-300 mt-1">
          {message.content}
        </p>

        {onReply && (
          <div className="flex w-full flex-row items-center justify-start gap-4 pt-3">
            <button
              onClick={() => onReply(message.id)}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-primary dark:hover:text-accent transition-colors"
            >
              <span className="material-symbols-outlined text-lg">reply</span>
              <span>Reply</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
