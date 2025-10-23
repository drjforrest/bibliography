'use client';

import { useState } from 'react';

interface MessageComposerProps {
  onSend: (content: string) => void;
  placeholder?: string;
}

export default function MessageComposer({ onSend, placeholder = 'Write a message...' }: MessageComposerProps) {
  const [content, setContent] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (content.trim()) {
      onSend(content);
      setContent('');
    }
  };

  return (
    <footer className="flex-shrink-0 bg-white dark:bg-gray-800 p-6 border-t border-gray-200 dark:border-gray-700">
      <form onSubmit={handleSubmit} className="flex items-start gap-4">
        <div
          className="bg-center bg-no-repeat aspect-square bg-cover rounded-full w-11 shrink-0"
          style={{
            backgroundImage: 'url("https://lh3.googleusercontent.com/aida-public/AB6AXuA9XcEFw2VwLpC5_4H4ZwRYWSfxCSF-8AMU1iRo7iT31x2YBPoje4H61KfQH3MoEsuU2J2HgD38YJ7rLCsaTKh6rON3Z4J3M_dT83i8lHETbe5fs1COejXiVmSCdbrBD0Lm-tR8-FGLK8lG7xecRlm8pws779lKpPI38ygWGD92hj1poC0RcUiWGyodp85ga95SjEkNLTZH6mFHEl7YHjXIFF-Odml7bBElOxorTsJlsvXgBxXnXuVaE_nw13d3WDScmgzW98AdNu20")',
          }}
        />
        <div className="flex-1">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="form-textarea w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-text-primary dark:text-white placeholder:text-gray-400 focus:ring-primary focus:border-primary"
            placeholder={placeholder}
            rows={3}
          />
          <div className="flex justify-end mt-2">
            <button
              type="submit"
              disabled={!content.trim()}
              className="flex items-center justify-center gap-2 rounded-lg h-10 px-5 bg-accent text-white text-sm font-bold leading-normal hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Send</span>
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </form>
    </footer>
  );
}
