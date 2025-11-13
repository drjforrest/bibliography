'use client';

import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { useEffect, useState } from 'react';

interface APIKeyStatus {
  openai_api_key_set: boolean;
  anthropic_api_key_set: boolean;
}

export default function APIKeySettings() {
  const { token } = useAuth();
  const [status, setStatus] = useState<APIKeyStatus | null>(null);
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

 useEffect(() => {
   if (token && isOpen) {
     fetchStatus();
   }
 }, [token, isOpen]);

 const fetchStatus = async () => {
   try {
     const response = await axios.get(
       `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/api-keys`,
       {
         headers: {
           'Authorization': `Bearer ${token}`,
         },
       }
     );
     setStatus(response.data);
   } catch (error) {
     console.error('Failed to fetch API key status:', error);
   }
 };

  const updateKeys = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const data: any = {};
      if (openaiKey.trim()) data.openai_api_key = openaiKey.trim();
      if (anthropicKey.trim()) data.anthropic_api_key = anthropicKey.trim();

      const response = await axios.put(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/api-keys`,
        data,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      setStatus(response.data);
      setOpenaiKey('');
      setAnthropicKey('');
      alert('API keys updated successfully!');
    } catch (error) {
      console.error('Failed to update API keys:', error);
      alert('Failed to update API keys. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition-colors"
      >
        <span className="material-symbols-outlined text-base">key</span>
        API Keys
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">AI API Keys</h3>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          <div className="space-y-4">
            {/* OpenAI Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                OpenAI API Key
                {status && (
                  <span className={`ml-2 text-xs px-2 py-1 rounded ${
                    status.openai_api_key_set
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                  }`}>
                    {status.openai_api_key_set ? 'Set' : 'Not Set'}
                  </span>
                )}
              </label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Anthropic Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Anthropic API Key
                {status && (
                  <span className={`ml-2 text-xs px-2 py-1 rounded ${
                    status.anthropic_api_key_set
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                  }`}>
                    {status.anthropic_api_key_set ? 'Set' : 'Not Set'}
                  </span>
                )}
              </label>
              <input
                type="password"
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                placeholder="sk-ant-..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              onClick={updateKeys}
              disabled={isLoading || (!openaiKey.trim() && !anthropicKey.trim())}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
            >
              {isLoading ? 'Updating...' : 'Update Keys'}
            </button>

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Your API keys are stored securely and used only for AI chat functionality.
              They enable you to use your own AI provider accounts instead of relying on system defaults.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}