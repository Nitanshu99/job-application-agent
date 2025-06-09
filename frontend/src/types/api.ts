// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    limit: number;
    offset: number;
    total_count: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

// User Types
export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  website_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfile extends User {
  skills: string[];
  experience_years?: number;
  education: Education[];
  work_experience: WorkExperience[];
  preferences: UserPreferences;
}

export interface Education {
  id: string;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date?: string;
  gpa?: number;
}

export interface WorkExperience {
  id: string;
  company: string;
  position: string;
  description: string;
  start_date: string;
  end_date?: string;
  is_current: boolean;
}

export interface UserPreferences {
  job_types: string[];
  preferred_locations: string[];
  salary_range: {
    min: number;
    max: number;
  };
  remote_work: boolean;
}

// Job Types
export interface Job {
  id: string;
  title: string;
  company: string;
  description: string;
  requirements: string[];
  location: string;
  job_type: 'full-time' | 'part-time' | 'contract' | 'internship';
  salary_range?: {
    min: number;
    max: number;
  };
  posted_date: string;
  application_deadline?: string;
  job_url: string;
  is_active: boolean;
  relevance_score?: number;
}

// Application Types
export interface Application {
  id: string;
  job_id: string;
  user_id: string;
  status: 'pending' | 'interview_scheduled' | 'rejected' | 'offer_received' | 'withdrawn';
  application_method: 'manual' | 'automated';
  applied_at: string;
  follow_up_date?: string;
  notes?: string;
  job: Job;
  documents: Document[];
  timeline: ApplicationTimelineEvent[];
}

export interface ApplicationTimelineEvent {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
}

// Document Types
export interface Document {
  id: string;
  user_id: string;
  document_type: 'resume' | 'cover_letter';
  title: string;
  content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

// Authentication Types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

// Error Types
export interface ApiError {
  detail: string;
  status_code: number;
  error_type?: string;
}
