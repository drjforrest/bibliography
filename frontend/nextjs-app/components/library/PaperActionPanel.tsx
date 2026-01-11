'use client';

import { useApi } from '@/lib/api';
import { usePodcastApi } from '@/lib/podcast-api';
import type { Paper } from '@/types';
import type { ActionCategory, PaperAction } from '@/types/actions';
import { actionDefinitions, categoryMetadata } from '@/types/actions';
import { useEffect, useMemo, useRef, useState } from 'react';

// Helper function to escape HTML entities to prevent XSS attacks
function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Helper function to open a report window with properly escaped content
function openReportWindow(title: string | undefined, reportTitle: string, content: string | undefined): void {
  const reportWindow = window.open('', '_blank');
  if (!reportWindow) return;

  const escapedTitle = escapeHtml(title || 'Untitled');
  const escapedReportTitle = escapeHtml(reportTitle);
  const escapedContent = escapeHtml(content || '');

  reportWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <title>${escapedReportTitle} - ${escapedTitle}</title>
      </head>
      <body style="font-family: system-ui; max-width: 900px; margin: 40px auto; padding: 20px; line-height: 1.6;">
        <h1>${escapedReportTitle}</h1>
        <h2>${escapedTitle}</h2>
        <div style="white-space: pre-wrap; margin-top: 20px;">${escapedContent}</div>
      </body>
    </html>
  `);
  reportWindow.document.close();
}

interface PaperActionPanelProps {
  paper: Paper;
  isOpen: boolean;
  onClose: () => void;
  onActionComplete?: (actionId: string) => void;
  buttonRef?: React.RefObject<HTMLButtonElement | HTMLDivElement>;
  // Future: support batch operations
  // papers?: Paper[];
}

export default function PaperActionPanel({
  paper,
  isOpen,
  onClose,
  onActionComplete,
  buttonRef,
}: PaperActionPanelProps) {
  const api = useApi();
  const podcastApi = usePodcastApi();
  const [actionStates, setActionStates] = useState<Record<string, { status?: PaperAction['status'] }>>({});
  const [isFavorited, setIsFavorited] = useState(false);

  // Check favorite status
  useEffect(() => {
    if (isOpen && paper) {
      api.isFavorited(paper.id)
        .then(result => setIsFavorited(result.is_favorited))
        .catch(() => setIsFavorited(false));
    }
  }, [isOpen, paper, api]);

  // Group actions by category
  const actionsByCategory = useMemo(() => {
    const actions: PaperAction[] = [
      // Find Related Papers
      {
        ...actionDefinitions['find-related']!,
        onClick: async (paperIds: number[]) => {
          // Trigger recommendations - parent will handle opening modal
          onActionComplete?.('find-related');
          onClose();
        },
      },
      // Chat with PDF
      {
        ...actionDefinitions['chat-with-pdf']!,
        onClick: async (paperIds: number[]) => {
          // Navigate to chat - parent component will handle
          onActionComplete?.('chat-with-pdf');
          onClose();
        },
      },
      // Manage Tags
      {
        ...actionDefinitions['manage-tags']!,
        onClick: async (paperIds: number[]) => {
          // Parent component will handle tag dialog
          onActionComplete?.('manage-tags');
          onClose();
        },
      },
      // Toggle Favorite
      {
        ...actionDefinitions['toggle-favorite']!,
        title: isFavorited ? 'Remove from Favorites' : 'Add to Favorites',
        icon: isFavorited ? 'star' : 'star_outline',
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'processing' } }));
            if (isFavorited) {
              await api.removeFavorite(paperId);
            } else {
              await api.addFavorite(paperId);
            }
            setIsFavorited(prev => !prev);
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'completed' } }));
            // Remove the completed status after 2 seconds
            setTimeout(() => {
              setActionStates(prev => {
                // Safely remove 'toggle-favorite' while keeping other states
                const { ['toggle-favorite']: _removed, ...rest } = prev;
                return rest;
              });
            }, 2000);
            onActionComplete?.('toggle-favorite');
          } catch (error) {
            console.error('Failed to toggle favorite:', error);
            setActionStates(prev => ({ ...prev, 'toggle-favorite': { status: 'error' } }));
          }
        },
        status: actionStates['toggle-favorite']?.status,
      },
      // Delete
      {
        ...actionDefinitions['delete']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          if (!confirm(`Are you sure you want to delete "${paper.title}"?`)) {
            return;
          }
          try {
            setActionStates(prev => ({ ...prev, 'delete': { status: 'processing' } }));
            await api.deletePaper(paperId);
            setActionStates(prev => ({ ...prev, 'delete': { status: 'completed' } }));
            onActionComplete?.('delete');
            // Parent will handle navigation/refresh
          } catch (error) {
            console.error('Failed to delete paper:', error);
            setActionStates(prev => ({ ...prev, 'delete': { status: 'error' } }));
            alert('Failed to delete paper. Please try again.');
          }
        },
        status: actionStates['delete']?.status,
      },
      // AI Report Generation Actions
      {
        ...actionDefinitions['generate-quick-summary']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-quick-summary': { status: 'processing' } }));
            const result = await api.generatePaperReport(paperId, 'quick-summary');
            openReportWindow(paper.title, 'Quick Summary', result.report_content);
            setActionStates(prev => ({ ...prev, 'generate-quick-summary': { status: 'completed' } }));
            onActionComplete?.('generate-quick-summary');
            onClose();
          } catch (error: any) {
            console.error('Failed to generate quick summary:', error);
            setActionStates(prev => ({ ...prev, 'generate-quick-summary': { status: 'error' } }));
            alert(error?.response?.data?.detail || 'Failed to generate report. Please check your API key configuration.');
          }
        },
        status: actionStates['generate-quick-summary']?.status,
      },
      {
        ...actionDefinitions['generate-comprehensive-analysis']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-comprehensive-analysis': { status: 'processing' } }));
            const result = await api.generatePaperReport(paperId, 'comprehensive');
            openReportWindow(paper.title, 'Comprehensive Analysis', result.report_content);
            setActionStates(prev => ({ ...prev, 'generate-comprehensive-analysis': { status: 'completed' } }));
            onActionComplete?.('generate-comprehensive-analysis');
            onClose();
          } catch (error: any) {
            console.error('Failed to generate comprehensive analysis:', error);
            setActionStates(prev => ({ ...prev, 'generate-comprehensive-analysis': { status: 'error' } }));
            alert(error?.response?.data?.detail || 'Failed to generate report. Please check your API key configuration.');
          }
        },
        status: actionStates['generate-comprehensive-analysis']?.status,
      },
      {
        ...actionDefinitions['generate-critical-appraisal']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-critical-appraisal': { status: 'processing' } }));
            const result = await api.generatePaperReport(paperId, 'critical-appraisal');
            openReportWindow(paper.title, 'Critical Appraisal', result.report_content);
            setActionStates(prev => ({ ...prev, 'generate-critical-appraisal': { status: 'completed' } }));
            onActionComplete?.('generate-critical-appraisal');
            onClose();
          } catch (error: any) {
            console.error('Failed to generate critical appraisal:', error);
            setActionStates(prev => ({ ...prev, 'generate-critical-appraisal': { status: 'error' } }));
            alert(error?.response?.data?.detail || 'Failed to generate report. Please check your API key configuration.');
          }
        },
        status: actionStates['generate-critical-appraisal']?.status,
      },
      {
        ...actionDefinitions['generate-methodology-assessment']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-methodology-assessment': { status: 'processing' } }));
            const result = await api.generatePaperReport(paperId, 'methodology');
            openReportWindow(paper.title, 'Methodology Assessment', result.report_content);
            setActionStates(prev => ({ ...prev, 'generate-methodology-assessment': { status: 'completed' } }));
            onActionComplete?.('generate-methodology-assessment');
            onClose();
          } catch (error: any) {
            console.error('Failed to generate methodology assessment:', error);
            setActionStates(prev => ({ ...prev, 'generate-methodology-assessment': { status: 'error' } }));
            alert(error?.response?.data?.detail || 'Failed to generate report. Please check your API key configuration.');
          }
        },
        status: actionStates['generate-methodology-assessment']?.status,
      },
      {
        ...actionDefinitions['generate-research-gaps']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-research-gaps': { status: 'processing' } }));
            const result = await api.generatePaperReport(paperId, 'research-gaps');
            openReportWindow(paper.title, 'Research Gap Analysis', result.report_content);
            setActionStates(prev => ({ ...prev, 'generate-research-gaps': { status: 'completed' } }));
            onActionComplete?.('generate-research-gaps');
            onClose();
          } catch (error: any) {
            console.error('Failed to generate research gap analysis:', error);
            setActionStates(prev => ({ ...prev, 'generate-research-gaps': { status: 'error' } }));
            alert(error?.response?.data?.detail || 'Failed to generate report. Please check your API key configuration.');
          }
        },
        status: actionStates['generate-research-gaps']?.status,
      },
      // Generate Podcast
      {
        ...actionDefinitions['generate-podcast']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-podcast': { status: 'processing' } }));
            
            if (!podcastApi.api) {
              throw new Error('Podcast API not initialized');
            }

            const result = await podcastApi.generatePodcast({
              paper_id: paperId,
              tts_provider: 'openai', // Default to OpenAI for now
            });

            setActionStates(prev => ({ ...prev, 'generate-podcast': { status: 'completed' } }));
            onActionComplete?.('generate-podcast');
            onClose();
            
            // Show success message with podcast info
            alert(`Podcast "${result.title}" generated successfully! You can find it in your podcasts library.`);
          } catch (error: any) {
            console.error('Failed to generate podcast:', error);
            setActionStates(prev => ({ ...prev, 'generate-podcast': { status: 'error' } }));
            const errorMessage = error?.response?.data?.detail || error.message || 'Failed to generate podcast. Please check your API key configuration.';
            alert(errorMessage);
          }
        },
        status: actionStates['generate-podcast']?.status,
      },
      // Generate Visual Abstract
      {
        ...actionDefinitions['generate-visual-abstract']!,
        onClick: async (paperIds: number[]) => {
          const paperId = paperIds[0] || paper.id;
          try {
            setActionStates(prev => ({ ...prev, 'generate-visual-abstract': { status: 'processing' } }));
            
            const result = await api.generateVisualAbstract(paperId, false);
            
            setActionStates(prev => ({ ...prev, 'generate-visual-abstract': { status: 'completed' } }));
            onActionComplete?.('generate-visual-abstract');
            onClose();
            
            // Show success message with image preview
            const imageUrl = api.getVisualAbstractImageUrl(result.id);
            const previewWindow = window.open('', '_blank');
            if (previewWindow) {
              previewWindow.document.write(`
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta charset="UTF-8">
                    <title>Visual Abstract - ${paper.title}</title>
                    <style>
                      body {
                        font-family: system-ui;
                        max-width: 1200px;
                        margin: 40px auto;
                        padding: 20px;
                        text-align: center;
                        background: #f5f5f5;
                      }
                      img {
                        max-width: 100%;
                        height: auto;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                      }
                      h1 {
                        color: #333;
                        margin-bottom: 20px;
                      }
                      .info {
                        margin-top: 20px;
                        color: #666;
                        font-size: 14px;
                      }
                    </style>
                  </head>
                  <body>
                    <h1>Visual Abstract</h1>
                    <p><strong>${paper.title}</strong></p>
                    <img src="${imageUrl}" alt="Visual Abstract" />
                    <div class="info">
                      <p>Visual abstract generated successfully! This image will be available for 30 days.</p>
                      <p>You can find it in your dashboard under Visual Abstracts.</p>
                    </div>
                  </body>
                </html>
              `);
              previewWindow.document.close();
            }
          } catch (error: any) {
            console.error('Failed to generate visual abstract:', error);
            setActionStates(prev => ({ ...prev, 'generate-visual-abstract': { status: 'error' } }));
            const errorMessage = error?.response?.data?.detail || error.message || 'Failed to generate visual abstract. Please check your API key configuration.';
            alert(errorMessage);
          }
        },
        status: actionStates['generate-visual-abstract']?.status,
      },
    ];

    // Group by category
    const grouped: Record<ActionCategory, PaperAction[]> = {
      'ai-powered': [],
      'organize': [],
      'share-export': [],
      'content': [],
      'manage': [],
    };

    actions.forEach(action => {
      grouped[action.category].push(action);
    });

    return grouped;
  }, [paper, isFavorited, api, podcastApi, actionStates, onActionComplete, onClose]);

  // Keyboard shortcuts
  useEffect(() => {
    if (typeof isOpen === 'undefined' || !isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Close on Escape
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Action shortcuts (when panel is open)
      // R - Find Related
      if (e.key === 'r' || e.key === 'R') {
        const action = actionsByCategory['ai-powered'].find(a => a.id === 'find-related');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // C - Chat
      if (e.key === 'c' || e.key === 'C') {
        const action = actionsByCategory['content'].find(a => a.id === 'chat-with-pdf');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // T - Tags
      if (e.key === 't' || e.key === 'T') {
        const action = actionsByCategory['organize'].find(a => a.id === 'manage-tags');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
      // F - Favorite
      if (e.key === 'f' || e.key === 'F') {
        const action = actionsByCategory['organize'].find(a => a.id === 'toggle-favorite');
        if (action && !action.disabled) {
          action.onClick([paper.id]);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, actionsByCategory, onClose, paper.id]);

  // Calculate position for dropdown (below action button, aligned to right)
  // MUST be before early return to follow Rules of Hooks
  const [position, setPosition] = useState<{
    top: number;
    right?: number;
    left?: number;
  }>({ top: 0, right: 0 });
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && buttonRef?.current) {
      const buttonEl = buttonRef.current instanceof HTMLElement
        ? buttonRef.current
        : (buttonRef.current as HTMLElement);
      
      const button = buttonEl.tagName === 'BUTTON'
        ? buttonEl
        : buttonEl.querySelector<HTMLElement>('button') || buttonEl;
      
      if (button) {
        const rect = button.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Dropdown dimensions (w-80 = 320px)
        const dropdownWidth = 320;
        const estimatedDropdownHeight = 400; // Reasonable estimate, will be clamped by max-h
        const gap = 8;
        const margin = 16; // Minimum margin from viewport edges
        
        // Calculate initial position (below button, aligned to right edge)
        let top = rect.bottom + gap;
        let right: number | undefined = viewportWidth - rect.right;
        let left: number | undefined = undefined;
        
        // Check bottom overflow - position above if not enough space below
        const spaceBelow = viewportHeight - rect.bottom - margin;
        const spaceAbove = rect.top - margin;
        if (spaceBelow < estimatedDropdownHeight && spaceAbove > spaceBelow) {
          // Position above button
          top = rect.top - estimatedDropdownHeight - gap;
          // Clamp to viewport if still too high
          if (top < margin) {
            top = margin;
          }
        } else {
          // Position below button
          // Clamp to viewport if would overflow bottom
          const maxTop = viewportHeight - estimatedDropdownHeight - margin;
          if (top > maxTop) {
            top = Math.max(margin, maxTop);
          }
        }
        
        // Check horizontal overflow
        // When using 'right', the dropdown's right edge is at the specified position
        // Dropdown extends leftward from that point
        const dropdownLeftEdge = viewportWidth - (right ?? 0) - dropdownWidth;
        
        if (dropdownLeftEdge < margin) {
          // Would overflow left - switch to left positioning
          // Align to button's left edge, but ensure it fits within viewport
          const proposedLeft = rect.left;
          const dropdownRightEdge = proposedLeft + dropdownWidth;
          
          if (dropdownRightEdge > viewportWidth - margin) {
            // Would overflow right - position to fit within viewport
            left = viewportWidth - dropdownWidth - margin;
          } else {
            // Align to button's left edge
            left = Math.max(margin, proposedLeft);
          }
          right = undefined;
        } else if (right && right < margin) {
          // Would overflow right - ensure minimum margin
          right = margin;
        }
        
        setPosition({ top, right, left });
      }
    }
  }, [isOpen, buttonRef]);

  // Early return AFTER all hooks
  if (!isOpen) return null;

  // Sort categories by order
  const sortedCategories = (Object.keys(categoryMetadata) as ActionCategory[]).sort(
    (a, b) => categoryMetadata[a].order - categoryMetadata[b].order
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
      />

      {/* Floating Dropdown Menu */}
      <div
        ref={menuRef}
        className="fixed z-50 w-80 max-h-[calc(100vh-120px)] bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden"
        style={{
          top: `${position.top}px`,
          ...(position.left !== undefined
            ? { left: `${position.left}px` }
            : { right: `${position.right ?? 0}px` }),
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
              {paper.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="ml-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors shrink-0"
            aria-label="Close menu"
          >
            <span className="material-symbols-outlined text-lg text-gray-600 dark:text-gray-400">
              close
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-2">
          {sortedCategories.map((category) => {
            const actions = actionsByCategory[category];
            if (actions.length === 0) return null;

            return (
              <div key={category} className="mb-2 last:mb-0">
                <div className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {categoryMetadata[category].label}
                </div>
                <div className="space-y-0.5">
                  {actions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => {
                        action.onClick([paper.id]);
                      }}
                      disabled={action.disabled || action.status === 'processing'}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-sm text-left transition-colors ${
                        action.disabled || action.status === 'processing'
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <span className="material-symbols-outlined text-xl text-gray-600 dark:text-gray-400 shrink-0">
                        {action.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            {action.title}
                          </span>
                          {action.badge && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              action.badge === 'new' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' :
                              action.badge === 'beta' ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' :
                              'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                            }`}>
                              {action.badge}
                            </span>
                          )}
                        </div>
                        {action.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                            {action.description}
                          </p>
                        )}
                      </div>
                      {action.status === 'processing' && (
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 border-t-[#4e989e] shrink-0" />
                      )}
                      {action.status === 'completed' && (
                        <span className="material-symbols-outlined text-lg text-green-600 dark:text-green-400 shrink-0">
                          check_circle
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
