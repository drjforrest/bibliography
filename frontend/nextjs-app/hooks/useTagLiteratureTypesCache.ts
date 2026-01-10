/**
 * Hook for caching tag literature types to reduce API calls
 */

import { useMemo, useState, useCallback } from 'react';
import { useApi } from '@/lib/api';
import type { LiteratureType, Paper, Tag, Topic } from '@/types';

// Simple in-memory cache
const tagTypeCache = new Map<number, LiteratureType | undefined>();
const cacheTimestamps = new Map<number, number>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useTagLiteratureTypesCache() {
  const api = useApi();
  const [isCalculating, setIsCalculating] = useState(false);

  const getCachedType = useCallback((tagId: number): LiteratureType | undefined => {
    const timestamp = cacheTimestamps.get(tagId);
    if (timestamp && Date.now() - timestamp < CACHE_TTL) {
      return tagTypeCache.get(tagId);
    }
    return undefined; // Cache expired or not found
  }, []);

  const calculateTagType = useCallback(async (tagId: number): Promise<LiteratureType | undefined> => {
    // Check cache first
    const cached = getCachedType(tagId);
    if (cached !== undefined) {
      return cached;
    }

    try {
      const tagPapersData = await api.getPapersByTag(tagId);
      if (tagPapersData.papers && tagPapersData.papers.length > 0) {
        const typeCounts: Record<string, number> = {};
        tagPapersData.papers.forEach((p: Paper) => {
          const type = p.literature_type || 'PEER_REVIEWED';
          typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        const entries = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
        const dominantType = entries.length > 0 ? (entries[0][0] as LiteratureType) : undefined;
        
        // Cache the result
        tagTypeCache.set(tagId, dominantType);
        cacheTimestamps.set(tagId, Date.now());
        
        return dominantType;
      }
    } catch (error) {
      console.warn(`Could not fetch papers for tag ${tagId}:`, error);
    }
    
    // Cache undefined for empty tags too
    tagTypeCache.set(tagId, undefined);
    cacheTimestamps.set(tagId, Date.now());
    return undefined;
  }, [api, getCachedType]);

  const calculateTagLiteratureTypes = useCallback(async (tags: Tag[]): Promise<Topic[]> => {
    setIsCalculating(true);
    try {
      const results = await Promise.all(
        tags.map(async (tag: Tag) => {
          const tagId = tag.id;
          const dominantLiteratureType = await calculateTagType(tagId);

          const children = await Promise.all(
            (tag.children || []).map(async (child: Tag) => {
              const childDominantType = await calculateTagType(child.id);
              return {
                id: child.id.toString(),
                name: child.name,
                dominantLiteratureType: childDominantType,
              };
            })
          );

          return {
            id: tag.id.toString(),
            name: tag.name,
            dominantLiteratureType,
            children,
          };
        })
      );
      return results;
    } finally {
      setIsCalculating(false);
    }
  }, [calculateTagType]);

  const invalidateCache = useCallback((tagId?: number) => {
    if (tagId) {
      tagTypeCache.delete(tagId);
      cacheTimestamps.delete(tagId);
    } else {
      // Clear all cache
      tagTypeCache.clear();
      cacheTimestamps.clear();
    }
  }, []);

  return {
    calculateTagLiteratureTypes,
    calculateTagType,
    invalidateCache,
    isCalculating,
  };
}
