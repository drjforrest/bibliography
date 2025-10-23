'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import TopicList from '@/components/messages/TopicList';
import MessageThread from '@/components/messages/MessageThread';
import MessageComposer from '@/components/messages/MessageComposer';
import type { MessageTopic, Message } from '@/types';

// Mock data
const mockTopics: MessageTopic[] = [
  {
    id: 'general',
    name: 'General Announcements',
    icon: 'campaign',
    unreadCount: 1,
    lastMessage: new Date(),
  },
  {
    id: 'research',
    name: 'Research Methodologies',
    icon: 'science',
  },
  {
    id: 'conferences',
    name: 'Upcoming Conferences',
    icon: 'groups',
  },
  {
    id: 'discussions',
    name: 'Paper-Specific Discussions',
    icon: 'description',
    unreadCount: 1,
  },
];

const mockMessages: Message[] = [
  {
    id: '1',
    topicId: 'general',
    userId: 'user1',
    user: {
      id: 'user1',
      name: 'Dr. Eleanor Vance',
      email: 'eleanor@example.com',
      avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBMNXPy3tkziIIN5AdGgxBYXE5l5MWIEx8yUwVMhv7ugVdwdDB1kmkg0XbUwpzUsdF6ieEUFKXCxxF594Yj94u7qkvmqMzuCdMn8nqxQhAg3lPWM4BMopj1ESgcWN6zahUYqam9fdH4yfVVGt9qHKFGznO_Qy6rUYnPpqwA3Uz3HI0EHOywz_h_iT1btv-CtTnwJyKZZ_6ghEPNUFniTbH1snzZtpVAyg2VG56Qx4zjZVCHNXzEofmiiawW1yarFdkQMry9nBij2luY',
    },
    content: 'Just a reminder that the deadline for conference submissions is this Friday. Please ensure all papers are uploaded to the shared drive by then.',
    createdAt: new Date(Date.now() - 7200000), // 2 hours ago
    replies: [
      {
        id: '2',
        topicId: 'general',
        userId: 'user2',
        user: {
          id: 'user2',
          name: 'Dr. Ben Carter',
          email: 'ben@example.com',
          avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBfwzE6V2DcmDn-oHpeU58twCywYFsrvTuYUKlAASLWdE0FCmVQlXHWqSzuQjNp8KKd2zI4AwjN7-RYfKvNkG8NN7m7a0opa2ZpCQ_Lck20bhRNBV_xaQ8pJJU6S32Q9Y34eaKEWMcWydl80OWnNzVIuBIlgpVTW0iMhT0oOp7JWsP-xDjKt0q_x5mBmA4BbaRlhx9D8l0GmSAHC-y2Pz7NURubznsHeg3HDVLPMA0fgrKwfWVZY8sBDRDip7bOk6Ji1lXto4ixDdK6',
        },
        content: "Thanks for the reminder, Eleanor. I've just uploaded mine. Looking forward to everyone's feedback.",
        createdAt: new Date(Date.now() - 3600000), // 1 hour ago
        parentId: '1',
      },
    ],
  },
  {
    id: '3',
    topicId: 'general',
    userId: 'user3',
    user: {
      id: 'user3',
      name: 'Dr. Olivia Chen',
      email: 'olivia@example.com',
      avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDDX5tsmUVQ72YlTPLkWrpLh7pkOxoJzfAgVU2cazQ-OItwDtcGx7mSDXq5Ci-vbsN_V3E1JR1cKBn8qxVpkpOZp-Qj0fiWhJM14twYwUA9OE3lfKRz_SZnkH1GE1kp-F1ln73_7q9mqp0S1LL1e452VDQZkwC5Mc2USMQIJn0kwaV9vr6f10DyxIOt6kZVn2GZiC177aqNR7z7wRd8L7dJjZ2sFpZxAAzdhMQxvlCZnWxH4g0SFTJGCT9Z58uaK02GRfsfBJPugIVu',
    },
    content: "Has anyone had a chance to review the new guidelines for the university's research grant proposals? I have a few questions.",
    createdAt: new Date(Date.now() - 2700000), // 45 minutes ago
  },
];

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [currentTopic] = useState('general');
  const router = useRouter();

  const handleSendMessage = (content: string) => {
    const newMessage: Message = {
      id: `${Date.now()}`,
      topicId: currentTopic,
      userId: 'current-user',
      user: {
        id: 'current-user',
        name: 'You',
        email: 'you@example.com',
      },
      content,
      createdAt: new Date(),
    };
    setMessages([...messages, newMessage]);
  };

  const handleReply = (messageId: string) => {
    // In a real app, this would open a reply composer
    console.log('Reply to message:', messageId);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background-light dark:bg-background-dark text-text-primary">
        {/* Left Column: Navigation Panel */}
        <aside className="w-1/4 bg-white dark:bg-gray-800 p-6 flex flex-col justify-between border-r border-gray-200 dark:border-gray-700">
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

          <TopicList topics={mockTopics} />
        </div>

        <button className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg h-11 px-4 bg-accent text-white text-sm font-bold leading-normal tracking-[0.015em] hover:bg-green-600 transition-colors">
          <span className="material-symbols-outlined">add</span>
          <span className="truncate">Add New Topic</span>
        </button>
      </aside>

      {/* Right Column: Message Thread */}
      <main className="w-3/4 flex flex-col h-screen">
        <header className="flex-shrink-0 bg-white dark:bg-gray-800 p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <h2 className="text-3xl font-extrabold tracking-tight text-primary dark:text-white">
              General Announcements
            </h2>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <MessageThread messages={messages} onReply={handleReply} />
        </div>

        <MessageComposer onSend={handleSendMessage} />
      </main>
      </div>
    </ProtectedRoute>
  );
}
