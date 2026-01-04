'use client';

import { useState } from 'react';
import { Mic, FileText, BarChart3, Presentation, Loader2 } from 'lucide-react';

interface GenerateContentPanelProps {
  paperId: number;
  paperTitle: string;
}

type GenerationType = 'podcast' | 'summary' | 'infographic' | 'slides';
type GenerationStatus = 'idle' | 'generating' | 'complete' | 'error';

interface GenerationState {
  type: GenerationType | null;
  status: GenerationStatus;
  progress?: string;
  result?: any;
  error?: string;
}

export default function GenerateContentPanel({ paperId, paperTitle }: GenerateContentPanelProps) {
  const [generation, setGeneration] = useState<GenerationState>({
    type: null,
    status: 'idle',
  });

  const handleGenerate = async (type: GenerationType) => {
    setGeneration({
      type,
      status: 'generating',
      progress: 'Initializing...',
    });

    try {
      // TODO: Replace with actual API calls
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setGeneration({
        type,
        status: 'complete',
        result: { message: `${type} generated successfully!` },
      });
    } catch (error) {
      setGeneration({
        type,
        status: 'error',
        error: error instanceof Error ? error.message : 'Generation failed',
      });
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Generate Content</h3>
        <p className="text-sm text-gray-500 mt-1">
          Create AI-powered summaries, podcasts, and more
        </p>
      </div>

      <div className="p-4 space-y-3">
        {/* Podcast Button */}
        <button
          onClick={() => handleGenerate('podcast')}
          disabled={generation.status === 'generating'}
          className="w-full flex items-start gap-3 p-3 text-left rounded-lg border-2 border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            {generation.type === 'podcast' && generation.status === 'generating' ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Mic className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900">Generate Podcast</div>
            <div className="text-sm text-gray-500">
              AI discussion explaining this paper
            </div>
          </div>
        </button>

        {/* Summary Button */}
        <button
          onClick={() => handleGenerate('summary')}
          disabled={generation.status === 'generating'}
          className="w-full flex items-start gap-3 p-3 text-left rounded-lg border-2 border-gray-200 hover:border-green-500 hover:bg-green-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            {generation.type === 'summary' && generation.status === 'generating' ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <FileText className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900">Generate Summary</div>
            <div className="text-sm text-gray-500">
              Key findings and takeaways
            </div>
          </div>
        </button>

        {/* Infographic Button */}
        <button
          onClick={() => handleGenerate('infographic')}
          disabled={generation.status === 'generating'}
          className="w-full flex items-start gap-3 p-3 text-left rounded-lg border-2 border-gray-200 hover:border-purple-500 hover:bg-purple-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            {generation.type === 'infographic' && generation.status === 'generating' ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <BarChart3 className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900">Create Infographic</div>
            <div className="text-sm text-gray-500">
              Visual summary of key data
            </div>
          </div>
        </button>

        {/* Slides Button */}
        <button
          onClick={() => handleGenerate('slides')}
          disabled={generation.status === 'generating'}
          className="w-full flex items-start gap-3 p-3 text-left rounded-lg border-2 border-gray-200 hover:border-orange-500 hover:bg-orange-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center group-hover:scale-110 transition-transform">
            {generation.type === 'slides' && generation.status === 'generating' ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Presentation className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-900">Generate Slides</div>
            <div className="text-sm text-gray-500">
              Presentation deck from paper
            </div>
          </div>
        </button>

        {/* Generation Status */}
        {generation.status === 'generating' && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 text-blue-700">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm font-medium">
                Generating {generation.type}...
              </span>
            </div>
            {generation.progress && (
              <p className="text-sm text-blue-600 mt-1">{generation.progress}</p>
            )}
          </div>
        )}

        {/* Success Message */}
        {generation.status === 'complete' && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="text-green-700 text-sm font-medium">
              ✓ {generation.type} created successfully!
            </div>
          </div>
        )}

        {/* Error Message */}
        {generation.status === 'error' && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-red-700 text-sm font-medium">
              Error: {generation.error}
            </div>
          </div>
        )}
      </div>

      {/* Info Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
        <p className="text-xs text-gray-500">
          Generations use your configured AI models. Settings in{' '}
          <a href="/profile" className="text-blue-600 hover:text-blue-700 underline">
            Profile
          </a>
        </p>
      </div>
    </div>
  );
}
