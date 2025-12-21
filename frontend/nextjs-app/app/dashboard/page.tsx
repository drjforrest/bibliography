"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import LibraryGrowthChart from "@/components/dashboard/LibraryGrowthChart";
import PapersByTopicChart from "@/components/dashboard/PapersByTopicChart";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/lib/api";
import type { DashboardStats, LiteratureTypeStats, Topic } from "@/types";
import { LITERATURE_TYPE_COLORS, LITERATURE_TYPE_LABELS, LiteratureType } from "@/types";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activityFeed, setActivityFeed] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [dashboardStats, tagsData, activityData, notificationsData] = await Promise.all([
          api.getDashboardStats(),
          api.getTagHierarchy(),
          api.getActivityFeed(10),
          api.getNotifications(false, 10, 0),
        ]);

        setStats(dashboardStats);
        setActivityFeed(activityData.activities || []);
        setNotifications(notificationsData.notifications || []);
        setUnreadCount(notificationsData.unread_count || 0);

        // Convert tags to topics for sidebar
        const convertedTopics: Topic[] = (tagsData.tags || []).map((tag: any) => ({
          id: tag.id.toString(),
          name: tag.name,
          children: tag.children?.map((child: any) => ({
            id: child.id.toString(),
            name: child.name,
          })),
        }));
        setTopics(convertedTopics);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [isLoaded, isSignedIn]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTypeColor = (litType: string): string => {
    const key = litType as LiteratureType;
    return LITERATURE_TYPE_COLORS[key] || LITERATURE_TYPE_COLORS.PEER_REVIEWED;
  };

  const getAvatarUrl = (user: any) => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    if (user.avatar_url) {
      return `${API_URL}${user.avatar_url}`;
    }
    const name = user.display_name || user.email;
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=40`;
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return formatDate(dateString);
  };

  const handleMarkNotificationAsRead = async (notificationId: number) => {
    try {
      await api.markNotificationAsRead(notificationId);
      // Refresh notifications
      const notificationsData = await api.getNotifications(false, 10, 0);
      setNotifications(notificationsData.notifications || []);
      setUnreadCount(notificationsData.unread_count || 0);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-background-light dark:bg-background-dark">
        <Sidebar topics={topics} />

        <main className="flex-1 p-6">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Overview of your evidence library
              </p>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <p className="text-gray-500 dark:text-gray-400">Loading dashboard...</p>
              </div>
            ) : error ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-800 dark:text-red-200">{error}</p>
              </div>
            ) : stats ? (
              <>
                {/* Statistics Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                  {/* Total Papers */}
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                          Total Papers
                        </p>
                        <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">
                          {stats.total_papers}
                        </p>
                      </div>
                      <span className="material-symbols-outlined text-4xl text-[#4e989e]">
                        description
                      </span>
                    </div>
                  </div>

                  {/* Literature Type Cards */}
                  {stats.by_literature_type.map((typeStats: LiteratureTypeStats) => (
                    <div
                      key={typeStats.literature_type}
                      className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                            {typeStats.label}
                          </p>
                          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">
                            {typeStats.count}
                          </p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getTypeColor(typeStats.literature_type)}`}>
                          {typeStats.literature_type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                  <PapersByTopicChart />
                  <LibraryGrowthChart />
                </div>

                {/* Activity Feed and Notifications Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                  {/* Activity Feed */}
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                    <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                      <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                        Team Activity
                      </h2>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        What others are annotating
                      </p>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      {activityFeed.length === 0 ? (
                        <div className="p-8 text-center">
                          <span className="material-symbols-outlined text-5xl text-gray-400 dark:text-gray-600 mb-3">
                            group
                          </span>
                          <p className="text-gray-600 dark:text-gray-400">
                            No recent activity from other users
                          </p>
                        </div>
                      ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                          {activityFeed.map((activity) => (
                            <div
                              key={activity.id}
                              className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                              onClick={() => router.push(`/papers/${activity.paper.id}`)}
                            >
                              <div className="flex items-start gap-3">
                                <img
                                  src={getAvatarUrl(activity.user)}
                                  alt={activity.user.display_name || activity.user.email}
                                  className="w-10 h-10 rounded-full"
                                />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                      {activity.user.display_name || activity.user.email}
                                    </span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      {formatTimeAgo(activity.created_at)}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                                    annotated <span className="font-medium text-gray-900 dark:text-gray-100">{activity.paper.title}</span>
                                  </p>
                                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                                    {activity.content}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Notifications */}
                  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                    <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center justify-between">
                        <div>
                          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                            Notifications
                          </h2>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            Where you&apos;ve been mentioned
                          </p>
                        </div>
                        {unreadCount > 0 && (
                          <span className="bg-[#4e989e] text-white px-3 py-1 rounded-full text-sm font-semibold">
                            {unreadCount}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="max-h-96 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <div className="p-8 text-center">
                          <span className="material-symbols-outlined text-5xl text-gray-400 dark:text-gray-600 mb-3">
                            notifications_none
                          </span>
                          <p className="text-gray-600 dark:text-gray-400">
                            No notifications yet
                          </p>
                        </div>
                      ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                          {notifications.map((notification) => (
                            <div
                              key={notification.id}
                              className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors ${
                                !notification.is_read ? 'bg-[#4e989e]/10 dark:bg-[#4e989e]/20' : ''
                              }`}
                              onClick={() => handleMarkNotificationAsRead(notification.id)}
                            >
                              <div className="flex items-start gap-3">
                                {notification.sender && (
                                  <img
                                    src={getAvatarUrl(notification.sender)}
                                    alt={notification.sender.display_name || notification.sender.email}
                                    className="w-10 h-10 rounded-full"
                                  />
                                )}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    {notification.sender && (
                                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                        {notification.sender.display_name || notification.sender.email}
                                      </span>
                                    )}
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      {formatTimeAgo(notification.created_at)}
                                    </span>
                                    {!notification.is_read && (
                                      <span className="w-2 h-2 bg-[#4e989e] rounded-full"></span>
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                                    {notification.notification_type === 'MENTION_IN_ANNOTATION'
                                      ? 'mentioned you in an annotation'
                                      : notification.notification_type === 'MENTION_IN_MESSAGE'
                                      ? 'mentioned you in a message'
                                      : 'notification'}
                                  </p>
                                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                                    {notification.content}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Recent Papers Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                  <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                          {stats.last_login ? 'New Since Last Login' : 'Recently Added Papers'}
                        </h2>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          {stats.last_login 
                            ? `${stats.new_since_last_login_count} papers added since ${formatDate(stats.last_login)}`
                            : `${stats.new_since_last_login_count} most recent papers`
                          }
                        </p>
                      </div>
                      {stats.new_since_last_login_count > 0 && (
                        <span className="bg-[#4e989e]/20 text-[#4e989e] dark:bg-[#4e989e]/30 dark:text-[#94d2bd] px-3 py-1 rounded-full text-sm font-semibold">
                          {stats.new_since_last_login_count} new
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="divide-y divide-gray-200 dark:divide-gray-700">
                    {stats.new_since_last_login.length === 0 ? (
                      <div className="p-8 text-center">
                        <span className="material-symbols-outlined text-5xl text-gray-400 dark:text-gray-600 mb-3">
                          check_circle
                        </span>
                        <p className="text-gray-600 dark:text-gray-400">
                          No new papers since your last visit
                        </p>
                      </div>
                    ) : (
                      stats.new_since_last_login.map((paper) => (
                        <div
                          key={paper.id}
                          className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                          onClick={() => router.push(`/papers/${paper.id}`)}
                        >
                          <div className="flex items-start gap-4">
                            <span className="material-symbols-outlined text-[#4e989e] mt-1">
                              description
                            </span>
                            <div className="flex-1 min-w-0">
                              <h3 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-1">
                                {paper.title}
                              </h3>
                              {paper.authors && paper.authors.length > 0 && (
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                                  {paper.authors.slice(0, 3).join(', ')}
                                  {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                                </p>
                              )}
                              <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-500">
                                <span>{formatDate(paper.created_at)}</span>
                                <span className={`px-2 py-0.5 rounded ${getTypeColor(paper.literature_type)}`}>
                                  {LITERATURE_TYPE_LABELS[paper.literature_type as LiteratureType] || paper.literature_type}
                                </span>
                              </div>
                            </div>
                            <span className="material-symbols-outlined text-gray-400">
                              chevron_right
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
