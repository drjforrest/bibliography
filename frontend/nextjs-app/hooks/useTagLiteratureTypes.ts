/**
 * Hook to calculate dominant literature types for tags
 * 
 * @deprecated Use useTagLiteratureTypesCache for better performance with caching
 * This hook is kept for backward compatibility but will be removed in future versions
 */

import { useTagLiteratureTypesCache } from './useTagLiteratureTypesCache';

export function useTagLiteratureTypes() {
  const { calculateTagLiteratureTypes } = useTagLiteratureTypesCache();
  return { calculateTagLiteratureTypes };
}
