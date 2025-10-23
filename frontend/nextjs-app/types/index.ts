// User types
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar?: string;
  is_active?: boolean;
  is_verified?: boolean;
}

// Paper/Book types
export interface Paper {
  id: number;
  title?: string;
  authors: string[];
  journal?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  year?: number;
  publication_date?: string;
  publication_year?: number;
  doi?: string;
  pmid?: string;
  arxiv_id?: string;
  abstract?: string;
  coverImage: string;
  keywords: string[];
  subject_areas: string[];
  tags: string[];
  confidence_score?: number;
  is_open_access?: boolean;
  processing_status: string;
  file_size?: number;
  created_at: string;
}

// Annotation types
export type AnnotationType =
  | "note"
  | "highlight"
  | "bookmark"
  | "underline"
  | "comment";

export interface Annotation {
  id: string | number;
  content: string;
  annotation_type?: AnnotationType;
  type?: AnnotationType;
  page_number?: number;
  page?: number;
  x_coordinate?: number;
  y_coordinate?: number;
  width?: number;
  height?: number;
  color?: string;
  is_private?: boolean;
  isPrivate?: boolean;
  paper_id?: number;
  paperId?: string;
  user_id?: string;
  userId?: string;
  user?: User;
  user_email?: string;
  created_at?: string;
  createdAt?: Date;
  quote?: string;
}

export interface AnnotationCreate {
  content: string;
  annotation_type?: AnnotationType;
  page_number?: number;
  x_coordinate?: number;
  y_coordinate?: number;
  width?: number;
  height?: number;
  color?: string;
  is_private?: boolean;
}

export interface AnnotationUpdate {
  content?: string;
  annotation_type?: AnnotationType;
  page_number?: number;
  x_coordinate?: number;
  y_coordinate?: number;
  width?: number;
  height?: number;
  color?: string;
  is_private?: boolean;
}

// Tag/Topic types (for organizing papers)
export interface Tag {
  id: number;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
  user_id: string;
  created_at: string;
  paper_count: number;
  children?: Tag[];
}

export interface TagCreate {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
}

export interface TagUpdate {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  parent_id?: number;
}

// Legacy Topic interface for backward compatibility
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
export type ViewMode = "grid" | "list";
export type SortOption = "date" | "title" | "author";

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
