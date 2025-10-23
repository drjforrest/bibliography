// User types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

// Paper/Book types
export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year?: number;
  doi?: string;
  abstract?: string;
  coverImage?: string;
  pdfUrl?: string;
  addedAt: Date;
  topics?: string[];
  isFavorite?: boolean;
}

// Annotation types
export type AnnotationType = 'highlight' | 'underline' | 'comment';

export interface Annotation {
  id: string;
  paperId: string;
  userId: string;
  user: User;
  type: AnnotationType;
  content: string;
  quote?: string;
  page?: number;
  position?: {
    x: number;
    y: number;
  };
  color?: string;
  createdAt: Date;
  isPrivate: boolean;
}

// Topic types
export interface Topic {
  id: string;
  name: string;
  children?: Topic[];
  paperCount?: number;
}

// Message Board types
export interface Message {
  id: string;
  topicId: string;
  userId: string;
  user: User;
  content: string;
  createdAt: Date;
  parentId?: string;
  replies?: Message[];
}

export interface MessageTopic {
  id: string;
  name: string;
  icon: string;
  unreadCount?: number;
  lastMessage?: Date;
}

// View types
export type ViewMode = 'grid' | 'list';
export type SortOption = 'date' | 'title' | 'author';

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
