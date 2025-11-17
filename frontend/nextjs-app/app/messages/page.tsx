'use client';

import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/layout/Header';
import MessageComposer from '@/components/messages/MessageComposer';
import MessageThread from '@/components/messages/MessageThread';
import TopicList from '@/components/messages/TopicList';
import { api } from '@/lib/api';
import type { Message, MessageTopic } from '@/types';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function MessagesPage() {
  const [topics, setTopics] = useState<MessageTopic[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTopicId, setCurrentTopicId] = useState<number | null>(null);
  const [isLoadingTopics, setIsLoadingTopics] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Fetch message topics on mount
  useEffect(() => {
    const fetchTopics = async () => {
      try {
        setIsLoadingTopics(true);
        const topicsData = await api.getMessageTopics();
        setTopics(topicsData);
        // Set first topic as current if available
        if (topicsData.length > 0 && !currentTopicId) {
          setCurrentTopicId(topicsData[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch message topics:', error);
        setError('Failed to load message topics');
      } finally {
        setIsLoadingTopics(false);
      }
    };

    fetchTopics();
  }, [currentTopicId]);

  // Fetch messages when topic changes
  useEffect(() => {
    if (!currentTopicId) return;

    const fetchMessages = async () => {
      try {
        setIsLoadingMessages(true);
        const messagesData = await api.getMessages(currentTopicId);
        setMessages(messagesData);
      } catch (error) {
        console.error('Failed to fetch messages:', error);
        setError('Failed to load messages');
      } finally {
        setIsLoadingMessages(false);
      }
    };

    fetchMessages();
  }, [currentTopicId]);

  const handleSendMessage = async (content: string) => {
    if (!currentTopicId) return;
    
    try {
      const newMessage = await api.createMessage({
        topic_id: currentTopicId,
        content,
      });

      // Add the new message to the current messages
      setMessages([...messages, newMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message');
    }
  };

  const handleReply = (messageId: number) => {
    // In a real app, this would open a reply composer
    console.log('Reply to message:', messageId);
  };

  const handleCreateTopic = async () => {
    const name = window.prompt('Enter topic name:');
    if (!name || !name.trim()) return;

    try {
      const newTopic = await api.createTopic({
        name: name.trim(),
        icon: 'chat_bubble',
      });
      setTopics([...topics, newTopic]);
      setCurrentTopicId(newTopic.id);
    } catch (error) {
      console.error('Failed to create topic:', error);
      setError('Failed to create topic');
    }
  };

  const handleRenameTopic = async (topicId: number, newName: string) => {
    try {
      const updatedTopic = await api.updateTopic(topicId, { name: newName });
      setTopics(topics.map(t => t.id === topicId ? updatedTopic : t));
    } catch (error) {
      console.error('Failed to rename topic:', error);
      setError('Failed to rename topic');
    }
  };

  const handleDeleteTopic = async (topicId: number) => {
    try {
      await api.deleteTopic(topicId);
      setTopics(topics.filter(t => t.id !== topicId));
      // If we deleted the current topic, select the first remaining one
      if (currentTopicId === topicId) {
        const remainingTopics = topics.filter(t => t.id !== topicId);
        setCurrentTopicId(remainingTopics.length > 0 ? remainingTopics[0].id : null);
      }
    } catch (error) {
      console.error('Failed to delete topic:', error);
      setError('Failed to delete topic');
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-background-light dark:bg-background-dark text-text-primary">
        <Header />
        <div className="flex flex-1">
          {/* Left Column: Navigation Panel */}
          <aside className="w-1/4 bg-white dark:bg-gray-800 p-6 flex flex-col justify-between border-r border-gray-200 dark:border-gray-700">
          {isLoadingTopics ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500 dark:text-gray-400">Loading topics...</p>
            </div>
          ) : error ? (
            <div className="text-center">
              <p className="text-red-500 dark:text-red-400 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-[#4e989e] text-white rounded-lg hover:bg-[#3d7a7f]"
              >
                Retry
              </button>
            </div>
          ) : (
            <>
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div
              className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-12"
              style={{
                backgroundImage: 'url("https://lh3.googleusercontent.com/aida-public/AB6AXuCcECkDV0tOZVSJPC32BjmcbNw0s3rbcqPQ8Z98zXs1AnSwzEMtJbRFpXBF-4O__Q3igb94REKNeFyLOJSk5PrK5PpPtYC3BOeD0vEItqhHq1ul35LpitKfWatDF9r6hjZn5N5Acr1TVdzMOUx3AA0kTxKyJlU9u-fW7gV8VMF0pMnxBmkzt-6AVA8eAD50B5v6cmdD8cannnQhVFcWSefobbT1bXC9c2PI26TJab6yJCkKtsseH2bns93hAw9y3KMfQnA_rcOtrRKP")',
              }}
            />
            <div className="flex flex-col">
              <h1 className="text-lg font-bold text-primary dark:text-white">Digital Library</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Professor Portal</p>
            </div>
          </div>

          <div className="mb-6">
            <label className="flex flex-col min-w-40 h-11 w-full">
              <div className="flex w-full flex-1 items-stretch rounded-lg h-full">
                <div className="text-gray-500 flex border-none bg-secondary dark:bg-gray-700 items-center justify-center pl-3 rounded-l-lg border-r-0">
                  <span className="material-symbols-outlined">search</span>
                </div>
                <input
                  className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-r-lg text-text-primary dark:text-white focus:outline-none focus:ring-0 border-none bg-secondary dark:bg-gray-700 h-full placeholder:text-gray-500 dark:placeholder-gray-400 px-2 text-sm"
                  placeholder="Search topics..."
                />
              </div>
            </label>
          </div>

          <TopicList
            topics={topics}
            currentTopicId={currentTopicId}
            onTopicSelect={setCurrentTopicId}
            onRenameTopic={handleRenameTopic}
            onDeleteTopic={handleDeleteTopic}
          />
        </div>

              <button
                onClick={handleCreateTopic}
                className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg h-11 px-4 bg-[#4e989e] text-white text-sm font-bold leading-normal tracking-[0.015em] hover:bg-[#3d7a7f] transition-colors"
              >
                <span className="material-symbols-outlined">add</span>
                <span className="truncate">Add New Topic</span>
              </button>
            </>
          )}
        </aside>

          {/* Right Column: Message Thread */}
          <main className="flex-1 flex flex-col">
      <header className="flex-shrink-0 bg-white dark:bg-gray-800 p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <h2 className="text-3xl font-extrabold tracking-tight text-primary dark:text-white">
            {topics.find(t => t.id === currentTopicId)?.name || 'Messages'}
          </h2>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoadingMessages ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 dark:text-gray-400">Loading messages...</p>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-red-500 dark:text-red-400">{error}</p>
          </div>
        ) : (
          <MessageThread messages={messages} onReply={handleReply} />
        )}
      </div>

      <MessageComposer onSend={handleSendMessage} />
    </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
