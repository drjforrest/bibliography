'use client';

import { api } from '@/lib/api';
import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type LiteratureTypeTab = 'PEER_REVIEWED' | 'GREY_LITERATURE' | 'NEWS';

interface PapersByTopicData {
  name: string;
  value: number;
}

export default function PapersByTopicChart() {
  const [activeTab, setActiveTab] = useState<LiteratureTypeTab>('PEER_REVIEWED');
  const [data, setData] = useState<PapersByTopicData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const result = await api.getPapersByTopicChart(activeTab);
        setData(result.data);
        setTotal(result.total);
      } catch (error) {
        console.error('Failed to fetch papers by topic:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [activeTab]);

  const tabs: { key: LiteratureTypeTab; label: string; color: string }[] = [
    { key: 'PEER_REVIEWED', label: 'Peer-Reviewed', color: 'bg-[#4e989e]' }, // Trust Green
    { key: 'GREY_LITERATURE', label: 'Grey Literature', color: 'bg-[#4e989e]' }, // Trust Green
    { key: 'NEWS', label: 'News', color: 'bg-[#cc9900]' }, // College Gold
  ];

  const getBarColor = () => {
    switch (activeTab) {
      case 'PEER_REVIEWED': return '#4e989e'; // Trust Green
      case 'GREY_LITERATURE': return '#4e989e'; // Trust Green
      case 'NEWS': return '#cc9900'; // College Gold
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          Papers by Topic
        </h2>

        {/* Tabs */}
        <div className="flex gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? `${tab.color} text-white`
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {total > 0 && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">
            {total} papers in top {data.length} topics
          </p>
        )}
      </div>

      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-80">
            <p className="text-gray-500 dark:text-gray-400">Loading chart...</p>
          </div>
        ) : data.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80">
            <span className="material-symbols-outlined text-5xl text-gray-400 dark:text-gray-600 mb-3">
              bar_chart
            </span>
            <p className="text-gray-600 dark:text-gray-400">
              No papers tagged yet in this category
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={data}
              margin={{ top: 10, right: 30, left: 0, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                height={100}
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#f3f4f6'
                }}
                labelStyle={{ color: '#f3f4f6' }}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Bar
                dataKey="value"
                name="Papers"
                fill={getBarColor()}
                radius={[8, 8, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
