'use client';

import { api } from '@/lib/api';
import type { Paper, Tag, TagCreate } from '@/types';
import { useEffect, useState } from 'react';

interface TagDialogProps {
  isOpen: boolean;
  onClose: () => void;
  paper: Paper;
  onTagChange?: () => void;
}

export default function TagDialog({ isOpen, onClose, paper, onTagChange }: TagDialogProps) {
  const [paperTags, setPaperTags] = useState<Tag[]>([]);
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [newTagName, setNewTagName] = useState('');
  const [showCreateTag, setShowCreateTag] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Load tags when dialog opens
  useEffect(() => {
    if (isOpen) {
      loadTags();
    }
  }, [isOpen, paper.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadTags = async () => {
    setIsLoading(true);
    try {
      // Load current paper tags
      const paperTagsResponse = await api.getPaperTags(paper.id);
      setPaperTags(paperTagsResponse.tags);

      // Load all available tags
      const allTagsResponse = await api.getTags({ flat: true });
      setAvailableTags(allTagsResponse.tags);
    } catch (error) {
      console.error('Failed to load tags:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddTag = async (tagId: number) => {
    try {
      await api.addTagToPaper(paper.id, tagId);
      await loadTags(); // Refresh tags
      onTagChange?.();
    } catch (error) {
      console.error('Failed to add tag:', error);
      alert('Failed to add tag. Please try again.');
    }
  };

  const handleRemoveTag = async (tagId: number) => {
    try {
      await api.removeTagFromPaper(paper.id, tagId);
      await loadTags(); // Refresh tags
      onTagChange?.();
    } catch (error) {
      console.error('Failed to remove tag:', error);
      alert('Failed to remove tag. Please try again.');
    }
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim()) return;

    try {
      const newTag: TagCreate = {
        name: newTagName.trim(),
      };
      await api.createTag(newTag);
      setNewTagName('');
      setShowCreateTag(false);
      await loadTags(); // Refresh available tags
    } catch (error) {
      console.error('Failed to create tag:', error);
      alert('Failed to create tag. Please try again.');
    }
  };

  // Filter available tags (exclude already assigned tags)
  const filteredAvailableTags = availableTags.filter(tag =>
    !paperTags.some(paperTag => paperTag.id === tag.id) &&
    tag.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Manage Tags
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="p-4 space-y-4 max-h-[calc(80vh-120px)] overflow-y-auto">
          {/* Current Tags Section */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Current Tags ({paperTags.length})
            </h4>
            {paperTags.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                No tags assigned to this paper
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {paperTags.map((tag) => (
                  <span
                    key={tag.id}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-[#4e989e]/10 text-[#4e989e] dark:bg-[#4e989e]/20 dark:text-[#94d2bd] rounded"
                  >
                    {tag.name}
                    <button
                      onClick={() => handleRemoveTag(tag.id)}
                      className="hover:bg-[#4e989e]/20 rounded-full p-0.5"
                      title="Remove tag"
                    >
                      <span className="material-symbols-outlined text-[12px]">close</span>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Add Tags Section */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Add Tags
            </h4>

            {/* Search */}
            <div className="relative mb-3">
              <input
                type="text"
                placeholder="Search tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-[#4e989e] focus:border-[#4e989e]"
              />
              <span className="absolute right-3 top-2.5 text-gray-400">
                <span className="material-symbols-outlined text-[16px]">search</span>
              </span>
            </div>

            {/* Create New Tag */}
            {!showCreateTag ? (
              <button
                onClick={() => setShowCreateTag(true)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[#4e989e] hover:bg-[#4e989e]/10 rounded-md transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">add</span>
                Create New Tag
              </button>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Tag name..."
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreateTag();
                    if (e.key === 'Escape') setShowCreateTag(false);
                  }}
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-[#4e989e] focus:border-[#4e989e]"
                />
                <button
                  onClick={handleCreateTag}
                  disabled={!newTagName.trim()}
                  className="px-3 py-2 bg-[#4e989e] text-white rounded-md text-sm hover:bg-[#3a7a7a] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[16px]">check</span>
                </button>
                <button
                  onClick={() => {
                    setShowCreateTag(false);
                    setNewTagName('');
                  }}
                  className="px-3 py-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              </div>
            )}

            {/* Available Tags */}
            {isLoading ? (
              <div className="text-center py-4">
                <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-[#4e989e]"></div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading tags...</p>
              </div>
            ) : filteredAvailableTags.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 italic py-2">
                {searchQuery ? 'No matching tags found' : 'No available tags to add'}
              </p>
            ) : (
              <div className="max-h-40 overflow-y-auto space-y-1">
                {filteredAvailableTags.slice(0, 10).map((tag) => (
                  <button
                    key={tag.id}
                    onClick={() => handleAddTag(tag.id)}
                    className="w-full flex items-center justify-between px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
                  >
                    <span>{tag.name}</span>
                    <span className="material-symbols-outlined text-[16px] text-[#4e989e]">add</span>
                  </button>
                ))}
                {filteredAvailableTags.length > 10 && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-1">
                    {filteredAvailableTags.length - 10} more tags available...
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}