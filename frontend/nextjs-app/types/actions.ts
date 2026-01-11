/**
 * Paper Action System Types
 * 
 * Designed to support both single-paper and future batch operations.
 */

export type ActionCategory = 
  | 'ai-powered'     // AI-generated content (summaries, podcasts, etc.)
  | 'organize'       // Organization actions (tags, favorites, collections)
  | 'share-export'   // Sharing and export actions
  | 'content'        // Content viewing actions
  | 'manage';        // Management actions (delete, archive, etc.)

export type ActionStatus = 
  | 'available'      // Action is ready to use
  | 'processing'     // Action is currently running
  | 'completed'      // Action has been completed
  | 'disabled'       // Action is not available
  | 'error';         // Action failed

export type ActionBadge = 
  | 'new'            // Recently added feature
  | 'pro'            // Premium feature
  | 'beta';          // Beta feature

export interface PaperAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: ActionCategory;
  onClick: (paperIds: number[]) => void | Promise<void>;
  status?: ActionStatus;
  badge?: ActionBadge;
  keyboardShortcut?: string;
  disabled?: boolean;
  // Future: batch support
  supportsBatch?: boolean;  // Whether this action can be applied to multiple papers
  batchLabel?: string;      // Label when multiple papers selected (e.g., "Tag Papers" vs "Tag Paper")
}

/**
 * Action definitions registry
 * This will be used to generate action cards in the panel
 */
export const actionDefinitions: Record<string, Omit<PaperAction, 'onClick'>> = {
  'find-related': {
    id: 'find-related',
    title: 'Find Related Papers',
    description: 'Discover similar papers using Semantic Scholar recommendations',
    icon: 'auto_awesome',
    category: 'ai-powered',
    badge: 'new',
    keyboardShortcut: 'R',
    supportsBatch: false, // Currently single-paper only
  },
  'chat-with-pdf': {
    id: 'chat-with-pdf',
    title: 'Chat with PDF',
    description: 'Ask questions and get answers from this paper',
    icon: 'chat',
    category: 'ai-powered',
    keyboardShortcut: 'C',
    supportsBatch: false, // Currently single-paper only
  },
  'manage-tags': {
    id: 'manage-tags',
    title: 'Manage Tags',
    description: 'Add or remove tags to organize your library',
    icon: 'tag',
    category: 'organize',
    keyboardShortcut: 'T',
    supportsBatch: true, // Future: batch tag management
    batchLabel: 'Tag Papers',
  },
  'toggle-favorite': {
    id: 'toggle-favorite',
    title: 'Add to Favorites', // Will be dynamic based on state
    description: 'Mark this paper as a favorite',
    icon: 'star_outline',
    category: 'organize',
    keyboardShortcut: 'F',
    supportsBatch: true,
    batchLabel: 'Favorite Papers',
  },
  'delete': {
    id: 'delete',
    title: 'Delete Paper',
    description: 'Remove this paper from your library',
    icon: 'delete',
    category: 'manage',
    keyboardShortcut: 'Del',
    supportsBatch: true,
    batchLabel: 'Delete Papers',
  },
  // Future actions (commented out until implemented)
  // 'generate-summary': {
  //   id: 'generate-summary',
  //   title: 'Generate Summary',
  //   description: 'Create an AI-generated summary of this paper',
  //   icon: 'summarize',
  //   category: 'ai-powered',
  //   supportsBatch: false,
  // },
  // 'create-podcast': {
  //   id: 'create-podcast',
  //   title: 'Create Podcast',
  //   description: 'Generate an audio podcast version of this paper',
  //   icon: 'podcasts',
  //   category: 'ai-powered',
  //   badge: 'beta',
  //   supportsBatch: false,
  // },
  // 'generate-infographic': {
  //   id: 'generate-infographic',
  //   title: 'Generate Infographic',
  //   description: 'Create a visual infographic from this paper',
  //   icon: 'insights',
  //   category: 'ai-powered',
  //   badge: 'beta',
  //   supportsBatch: false,
  // },
};

/**
 * Category metadata for display
 */
export const categoryMetadata: Record<ActionCategory, { label: string; icon: string; order: number }> = {
  'ai-powered': {
    label: 'AI-Powered Actions',
    icon: 'auto_awesome',
    order: 1,
  },
  'organize': {
    label: 'Organization',
    icon: 'folder',
    order: 2,
  },
  'share-export': {
    label: 'Sharing & Export',
    icon: 'share',
    order: 3,
  },
  'content': {
    label: 'Content',
    icon: 'description',
    order: 4,
  },
  'manage': {
    label: 'Management',
    icon: 'settings',
    order: 5,
  },
};
