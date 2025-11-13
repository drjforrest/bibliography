// User types
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar?: string;
  is_active?: boolean;
  is_verified?: boolean;
}

// Literature types
export type LiteratureType = 'PEER_REVIEWED' | 'GREY_LITERATURE' | 'NEWS';

export const LITERATURE_TYPE_LABELS: Record<LiteratureType, string> = {
  PEER_REVIEWED: 'Peer-Reviewed',
  GREY_LITERATURE: 'Grey Literature',
  NEWS: 'News & Media'
};

export const LITERATURE_TYPE_COLORS: Record<LiteratureType, string> = {
  PEER_REVIEWED: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  GREY_LITERATURE: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  NEWS: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
};

// Paper/Book types
export interface Paper {
  id: number;
  literature_type?: LiteratureType;  // Type of literature (peer-reviewed, grey, news)
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
  summary?: string;  // DEVONthink Finder Comment (article summary)
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

// Dashboard types
export interface LiteratureTypeStats {
  literature_type: string;
  count: number;
  label: string;
}

export interface RecentPaper {
  id: number;
  title: string;
  authors?: string[];
  created_at: string;
  literature_type: string;
}

export interface DashboardStats {
  total_papers: number;
  by_literature_type: LiteratureTypeStats[];
  new_since_last_login: RecentPaper[];
  new_since_last_login_count: number;
  last_login?: string;
}
