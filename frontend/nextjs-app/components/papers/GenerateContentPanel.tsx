'use client';

import { useState, useEffect } from 'react';
import { Mic, FileText, BarChart3, Presentation, Loader2, DollarSign } from 'lucide-react';
import { useAuth } from '@clerk/nextjs';
import { podcastAPI, type Podcast } from '@/lib/podcast-api';

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
  result?: Podcast | any;
  error?: string;
}

interface Balance {
  balance: number;
  usage: number;
  limit: number;
  is_free_tier: boolean;
}

export default function GenerateContentPanel({ paperId, paperTitle }: GenerateContentPanelProps) {
  const { getToken } = useAuth();
  const [generation, setGeneration] = useState<GenerationState>({
    type: null,
    status: 'idle',
  });
  const [balance, setBalance] = useState<Balance | null>(null);
  const [loadingBalance, setLoadingBalance] = useState(false);

  // Fetch balance on mount
  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    try {
      setLoadingBalance(true);
      const token = await getToken();
      if (!token) return;

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/openrouter/balance`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setBalance(data);
      }
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    } finally {
      setLoadingBalance(false);
    }
  };

  const handleGenerate = async (type: GenerationType) => {
    setGeneration({
      type,
      status: 'generating',
      progress: 'Initializing...',
    });

    try {
      const token = await getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      if (type === 'podcast') {
        setGeneration(prev => ({ ...prev, progress: 'Generating script...' }));
        
        const podcast = await podcastAPI.generatePodcast(
          { paper_id: paperId },
          token
        );
        
        setGeneration({
          type,
          status: 'complete',
          result: podcast,
        });
      } else if (type === 'infographic') {
        setGeneration(prev => ({ ...prev, progress: 'Creating visual infographic...' }));
        
        // TODO: Create infographicAPI similar to podcastAPI
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/infographics/generate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ 
            paper_id: paperId,
            style: 'modern',
            focus: 'all'
          }),
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to generate infographic');
        }
        
        const infographic = await response.json();
        
        setGeneration({
          type,
          status: 'complete',
          result: infographic,
        });
      } else {
        // TODO: Implement other generation types
        throw new Error(`${type} generation not yet implemented`);
      }
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

        {/* Success Message with Content Display */}
        {generation.status === 'complete' && generation.result && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg space-y-3">
            <div className="text-green-700 text-sm font-medium">
              ✓ {generation.type} created successfully!
            </div>
            
            {/* Podcast Player */}
            {generation.type === 'podcast' && generation.result && (
              <div className="bg-white rounded-lg p-4 border border-gray-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900 text-sm">
                      {generation.result.title}
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {Math.floor(generation.result.duration_seconds / 60)}:
                      {(generation.result.duration_seconds % 60).toString().padStart(2, '0')} • {' '}
                      {generation.result.tts_provider}
                    </p>
                  </div>
                </div>
                
                {/* Audio Player */}
                <audio 
                  controls 
                  className="w-full"
                  src={podcastAPI.getDownloadUrl(generation.result.id)}
                >
                  Your browser does not support the audio element.
                </audio>
                
                {/* Transcript Toggle */}
                <details className="text-sm">
                  <summary className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium">
                    View Transcript
                  </summary>
                  <div className="mt-2 p-3 bg-gray-50 rounded text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {generation.result.podcast_transcript}
                  </div>
                </details>
              </div>
            )}
            
            {/* Infographic Display */}
            {generation.type === 'infographic' && generation.result && (
              <div className="bg-white rounded-lg p-4 border border-gray-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900 text-sm">
                      {generation.result.title}
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {generation.result.style} style • {generation.result.focus_area}
                    </p>
                  </div>
                </div>
                
                {/* Image Display */}
                <div className="relative">
                  <img 
                    src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/infographics/${generation.result.id}/download`}
                    alt={generation.result.title}
                    className="w-full rounded-lg border border-gray-200"
                  />
                </div>
                
                {/* Download Button */}
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/infographics/${generation.result.id}/download`}
                  download={`infographic_${generation.result.id}.png`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
                >
                  Download PNG
                </a>
              </div>
            )}
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

      {/* Info Footer with Balance */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg space-y-2">
        {/* Balance Display */}
        {balance && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-600 flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              OpenRouter Balance
            </span>
            <span className="font-medium text-gray-900">
              ${balance.balance.toFixed(2)} remaining
            </span>
          </div>
        )}
        
        {loadingBalance && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Loader2 className="w-3 h-3 animate-spin" />
            Checking balance...
          </div>
        )}
        
        {/* Settings Link */}
        <p className="text-xs text-gray-500">
          Generations use your OpenRouter API key.{' '}
          <a href="/profile" className="text-blue-600 hover:text-blue-700 underline">
            Settings
          </a>
          {' • '}
          <a 
            href="https://openrouter.ai/credits" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-700 underline"
          >
            Add Credits
          </a>
        </p>
      </div>
    </div>
  );
}
