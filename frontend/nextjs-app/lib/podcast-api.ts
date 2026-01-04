/**
 * API client for v2.0 podcast generation endpoints
 */

import { getApiBaseUrl } from './api';

export interface PodcastGenerateRequest {
  paper_id: number;
  model?: string;
  tts_provider?: 'auto' | 'kokoro' | 'openai' | 'elevenlabs';
  voice?: string;
}

export interface PodcastGenerateMultiRequest {
  paper_ids: number[];
  model?: string;
  tts_provider?: 'auto' | 'kokoro' | 'openai' | 'elevenlabs';
  voice?: string;
  focus?: string;
}

export interface Podcast {
  id: number;
  user_id: number;
  source_paper_ids: number[];
  title: string;
  podcast_transcript: string;
  duration_seconds: number;
  file_location: string;
  generation_model: string;
  tts_provider: string;
  created_at: string;
}

export class PodcastAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = `${getApiBaseUrl()}/api/v2/podcasts`;
  }

  /**
   * Generate a podcast from a single paper
   */
  async generatePodcast(request: PodcastGenerateRequest, token: string): Promise<Podcast> {
    const response = await fetch(`${this.baseUrl}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate podcast');
    }

    return response.json();
  }

  /**
   * Generate a comparative podcast from multiple papers
   */
  async generateMultiPaperPodcast(
    request: PodcastGenerateMultiRequest,
    token: string
  ): Promise<Podcast> {
    const response = await fetch(`${this.baseUrl}/generate-multi`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate podcast');
    }

    return response.json();
  }

  /**
   * List all podcasts for the current user
   */
  async listPodcasts(token: string, limit: number = 50, offset: number = 0): Promise<Podcast[]> {
    const response = await fetch(
      `${this.baseUrl}?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch podcasts');
    }

    return response.json();
  }

  /**
   * Get a specific podcast by ID
   */
  async getPodcast(podcastId: number, token: string): Promise<Podcast> {
    const response = await fetch(`${this.baseUrl}/${podcastId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch podcast');
    }

    return response.json();
  }

  /**
   * Delete a podcast
   */
  async deletePodcast(podcastId: number, token: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${podcastId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to delete podcast');
    }
  }

  /**
   * Get download URL for podcast audio
   */
  getDownloadUrl(podcastId: number): string {
    return `${this.baseUrl}/${podcastId}/download`;
  }
}

// Export singleton instance
export const podcastAPI = new PodcastAPI();
