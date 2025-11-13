'use client';

import { useAuth } from '@/contexts/AuthContext';
import type { Topic } from '@/types';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import APIKeySettings from './APIKeySettings';

interface SidebarProps {
  topics?: Topic[];
}

export default function Sidebar({ topics = [] }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const isActive = (path: string) => pathname === path;

  const navItems = [
    { icon: 'dashboard', label: 'Dashboard', href: '/dashboard' },
    { icon: 'select_all', label: 'All', href: '/' },
    { icon: 'folder_open', label: 'Topics', href: '/topics' },
    { icon: 'bookmark', label: 'Favorites', href: '/favorites' },
    { icon: 'history', label: 'Recently Added', href: '/recent' },
    { icon: 'forum', label: 'Message Board', href: '/messages' },
  ];

  return (
    <aside className="w-64 bg-[#f6f7f8] dark:bg-[#101922] p-4 flex flex-col justify-between border-r border-gray-200 dark:border-gray-800">
      <div>
        {/* Logo and User Info */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-3 mb-8 w-full hover:bg-gray-100 dark:hover:bg-gray-800 p-2 rounded-lg transition-colors"
          >
            <Image
              src="/HERO-Lab-logo-no-words.png"
              alt="HERO Lab Logo"
              width={40}
              height={40}
              className="rounded-full"
            />
            <div className="flex flex-col flex-1 text-left">
              <h1 className="text-base font-medium leading-normal text-gray-900 dark:text-white">
                {user?.name || 'Digital Library'}
              </h1>
              <p className="text-sm font-normal leading-normal text-gray-500 dark:text-gray-400 truncate">
                {user?.email || 'user@example.com'}
              </p>
            </div>
            <span className="material-symbols-outlined text-gray-500 dark:text-gray-400">
              {showUserMenu ? 'expand_less' : 'expand_more'}
            </span>
          </button>

          {/* User Menu Dropdown */}
          {showUserMenu && (
            <div className="absolute top-full left-0 right-0 mb-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              <button
                onClick={() => {
                  logout();
                  setShowUserMenu(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <span className="material-symbols-outlined">logout</span>
                <span className="text-sm font-medium">Sign out</span>
              </button>
            </div>
          )}
        </div>

        {/* API Key Settings */}
        <div className="mb-6">
          <APIKeySettings />
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg ${
                isActive(item.href)
                  ? 'bg-primary/20 dark:bg-primary/30 text-primary dark:text-white'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800'
              }`}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <p className="text-sm font-medium leading-normal">{item.label}</p>
            </Link>
          ))}
        </nav>

        {/* Topics Section */}
        <div className="mt-8">
          <h2 className="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            Topics
          </h2>
          <ul className="space-y-2">
            {topics.slice(0, 3).map((topic) => (
              <li key={topic.id}>
                <Link
                  href={`/topics/${topic.id}`}
                  className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800"
                >
                  {topic.name}
                </Link>
                {topic.children && topic.children.length > 0 && (
                  <ul className="pl-6 mt-1 space-y-1">
                    {topic.children.map((child) => (
                      <li key={child.id}>
                        <Link
                          href={`/topics/${child.id}`}
                          className="block text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                        >
                          {child.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
