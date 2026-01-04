'use client';

import { createAuthenticatedClient } from '@/lib/api';
import { useAuth } from '@clerk/nextjs';
import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface GrowthData {
  date: string;
  count: number;
}

export default function LibraryGrowthChart() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [data, setData] = useState<GrowthData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [days, setDays] = useState(90);

  // Create authenticated API client
  const authenticatedApi = useMemo(() => createAuthenticatedClient(getToken), [getToken]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) {
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const result = await authenticatedApi.get('/api/v1/dashboard/growth-over-time', { params: { days } }).then(r => r.data);
        setData(result.data);
        setTotal(result.total);
      } catch (error) {
        console.error('Failed to fetch growth data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [days, isLoaded, isSignedIn, authenticatedApi]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const timeRanges = [
    { label: '30 Days', value: 30 },
    { label: '90 Days', value: 90 },
    { label: '180 Days', value: 180 },
    { label: '1 Year', value: 365 },
  ];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Library Growth Over Time
            </h2>
            {total > 0 && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {total} total papers in library
              </p>
            )}
          </div>

          {/* Time Range Selector */}
          <div className="flex gap-2">
            {timeRanges.map((range) => (
              <button
                key={range.value}
                onClick={() => setDays(range.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  days === range.value
                    ? 'bg-[#4e989e] text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-gray-500 dark:text-gray-400">Loading chart...</p>
          </div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80">
            <span className="material-symbols-outlined text-5xl text-gray-400 dark:text-gray-600 mb-3">
              trending_up
            </span>
            <p className="text-gray-600 dark:text-gray-400">
              No data available for the selected time range
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart
              data={data}
              margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
            >
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4e989e" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#4e989e" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fill: '#6b7280', fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 12 }}
                label={{ value: 'Total Papers', angle: -90, position: 'insideLeft', fill: '#6b7280' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#f3f4f6'
                }}
                labelStyle={{ color: '#f3f4f6' }}
                labelFormatter={(value) => formatDate(value as string)}
                formatter={(value) => [typeof value === 'number' ? value : 0, 'Total Papers']}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#4e989e"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorCount)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}

        {data.length > 0 && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400">Starting Count</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {data[0]?.count || 0}
              </p>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400">Papers Added</p>
              <p className="text-2xl font-bold text-[#4e989e] dark:text-[#4e989e] mt-1">
                +{(data[data.length - 1]?.count || 0) - (data[0]?.count || 0)}
              </p>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400">Current Total</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {data[data.length - 1]?.count || 0}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
