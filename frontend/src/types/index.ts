// User Types
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfile extends User {
  phone?: string;
  location?: string;
  preferred_job_titles?: string[];
  preferred_industries?: string[];
  preferred_salary_min?: number;
  preferred_salary_max?: number;
  preferred_work_type?: 'remote' | 'hybrid' | 'onsite' | 'no_preference';
  skills?: string[];
  experience_years?: number;
}

export interface UserCreate {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

export interface UserUpdate {
  full_name?: string;
  phone?: string;
  location?: string;
  preferred_job_titles?: string[];
  preferred_industries?: string[];
  preferred_salary_min?: number;
  preferred_salary_max?: number;
  preferred_work_type?: 'remote' | 'hybrid' | 'onsite' | 'no_preference';
  skills?: string[];
  experience_years?: number;
}

// Auth Types
export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

// Job Types
export interface Job {
  id: string;
  title: string;
  company: string;
  location?: string;
  description: string;
  requirements?: string[];
  salary_min?: number;
  salary_max?: number;
  job_type?: 'full_time' | 'part_time' | 'contract' | 'remote';
  experience_level?: 'entry' | 'mid' | 'senior' | 'executive';
  source_url: string;
  portal_name: string;
  posted_date?: string;
  scraped_at: string;
  match_score?: number;
  created_at: string;
  updated_at: string;
}

export interface JobSearchFilters {
  query?: string;
  location?: string;
  job_type?: string;
  experience_level?: string;
  salary_min?: number;
  salary_max?: number;
  company?: string;
  portal?: string;
}

// Application Types
export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  job: Job;
  status: 'pending' | 'applied' | 'interview' | 'offer' | 'rejected' | 'withdrawn';
  applied_date: string;
  last_status_update: string;
  resume_id?: string;
  cover_letter_id?: string;
  notes?: string;
  application_method: 'manual' | 'auto_ai';
  response_received?: boolean;
  interview_date?: string;
  follow_up_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  job_id: string;
  resume_id?: string;
  cover_letter_id?: string;
  notes?: string;
  application_method?: 'manual' | 'auto_ai';
}

export interface ApplicationUpdate {
  status?: 'pending' | 'applied' | 'interview' | 'offer' | 'rejected' | 'withdrawn';
  notes?: string;
  response_received?: boolean;
  interview_date?: string;
  follow_up_date?: string;
}

// Document Types
export interface Document {
  id: string;
  user_id: string;
  title: string;
  type: 'resume' | 'cover_letter';
  content: string;
  template?: string;
  job_id?: string;
  generated_by_ai: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentCreate {
  title: string;
  type: 'resume' | 'cover_letter';
  content?: string;
  template?: string;
  job_id?: string;
  job_description?: string;
  skills_to_highlight?: string[];
}

// Portal Types
export interface JobPortal {
  id: string;
  name: string;
  url: string;
  type: 'company_careers' | 'job_board' | 'recruitment_platform';
  is_active: boolean;
  last_sync: string;
  jobs_found: number;
  auto_sync_frequency: 'hourly' | 'daily' | 'weekly' | 'manual';
  created_at: string;
  updated_at: string;
}

export interface JobPortalCreate {
  name: string;
  url: string;
  type: 'company_careers' | 'job_board' | 'recruitment_platform';
  auto_sync_frequency?: 'hourly' | 'daily' | 'weekly' | 'manual';
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Statistics Types
export interface DashboardStats {
  total_applications: number;
  pending_applications: number;
  interviews_scheduled: number;
  offers_received: number;
  applications_this_week: number;
  applications_this_month: number;
  response_rate: number;
  success_rate: number;
  average_response_time: number;
}

export interface ApplicationStats {
  total_applications: number;
  by_status: Record<string, number>;
  by_month: Array<{ month: string; count: number }>;
  by_portal: Array<{ portal: string; count: number }>;
  response_rate: number;
}

// AI Processing Types
export interface AIProcessingStatus {
  phi3_status: 'ready' | 'processing' | 'error';
  gemma_status: 'ready' | 'processing' | 'error';
  mistral_status: 'ready' | 'processing' | 'error';
  current_task?: string;
  progress?: number;
}

// Duplicate Detection Types
export interface DuplicateCheck {
  is_duplicate: boolean;
  similarity_score: number;
  existing_application?: Application;
  reasons: string[];
}

// Form Types
export interface JobSearchForm {
  query: string;
  location: string;
  job_type: string;
  experience_level: string;
  salary_range: string;
}
