#!/bin/bash

# Complete Frontend Integration Setup Script
# This script creates all the necessary files for frontend-backend integration

set -e

echo "🚀 Creating Complete Frontend Integration..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the frontend directory."
    exit 1
fi

echo "📁 Creating directory structure..."
mkdir -p src/services
mkdir -p src/types  
mkdir -p src/hooks
mkdir -p src/utils
mkdir -p src/context
mkdir -p src/components/common
mkdir -p src/app/dashboard

echo "📝 Creating API types..."
cat > src/types/api.ts << 'EOF'
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
EOF

echo "🔐 Creating authentication utilities..."
cat > src/utils/auth.ts << 'EOF'
import Cookies from 'js-cookie';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'user_data';

export const setAuthToken = (token: string): void => {
  Cookies.set(TOKEN_KEY, token, { 
    expires: 7, // 7 days
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict'
  });
};

export const getAuthToken = (): string | undefined => {
  return Cookies.get(TOKEN_KEY);
};

export const removeAuthToken = (): void => {
  Cookies.remove(TOKEN_KEY);
  Cookies.remove(USER_KEY);
};

export const setUserData = (user: any): void => {
  Cookies.set(USER_KEY, JSON.stringify(user), {
    expires: 7,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict'
  });
};

export const getUserData = (): any | null => {
  const userData = Cookies.get(USER_KEY);
  return userData ? JSON.parse(userData) : null;
};

export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};
EOF

echo "🌐 Creating API service..."
cat > src/services/api.ts << 'EOF'
import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { toast } from 'react-hot-toast';
import { getAuthToken, removeAuthToken, setAuthToken } from '../utils/auth';
import type {
  ApiResponse,
  PaginatedResponse,
  User,
  UserProfile,
  Job,
  Application,
  Document,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  ApiError
} from '../types/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = getAuthToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const message = error.response?.data?.detail || 'An unexpected error occurred';
        
        if (error.response?.status === 401) {
          removeAuthToken();
          toast.error('Session expired. Please login again.');
          window.location.href = '/login';
        } else if (error.response?.status >= 500) {
          toast.error('Server error. Please try again later.');
        } else if (error.response?.status === 422) {
          toast.error('Invalid data. Please check your input.');
        } else {
          toast.error(message);
        }

        return Promise.reject(error);
      }
    );
  }

  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    url: string,
    data?: any,
    params?: any
  ): Promise<T> {
    const response: AxiosResponse<T> = await this.client.request({
      method,
      url,
      data,
      params,
    });
    return response.data;
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await this.client.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const { access_token } = response.data;
    setAuthToken(access_token);
    
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<ApiResponse<User>> {
    return this.request<ApiResponse<User>>('POST', '/auth/register', userData);
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('POST', '/auth/logout');
    } finally {
      removeAuthToken();
    }
  }

  async refreshToken(): Promise<LoginResponse> {
    return this.request<LoginResponse>('POST', '/auth/refresh');
  }

  // User endpoints
  async getUserProfile(): Promise<UserProfile> {
    return this.request<UserProfile>('GET', '/users/profile');
  }

  async updateUserProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    return this.request<UserProfile>('PUT', '/users/profile', data);
  }

  async getUserStatistics(): Promise<any> {
    return this.request<any>('GET', '/users/statistics');
  }

  // Job endpoints
  async searchJobs(params: {
    query?: string;
    location?: string;
    job_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Job>> {
    return this.request<PaginatedResponse<Job>>('GET', '/jobs/search', undefined, params);
  }

  async getJob(id: string): Promise<Job> {
    return this.request<Job>('GET', `/jobs/${id}`);
  }

  async saveJob(jobId: string): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('POST', `/jobs/${jobId}/save`);
  }

  async unsaveJob(jobId: string): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>('DELETE', `/jobs/${jobId}/save`);
  }

  async getSavedJobs(): Promise<PaginatedResponse<Job>> {
    return this.request<PaginatedResponse<Job>>('GET', '/jobs/saved');
  }

  // Application endpoints
  async getApplications(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<Application>> {
    return this.request<PaginatedResponse<Application>>('GET', '/applications', undefined, params);
  }

  async getApplication(id: string): Promise<Application> {
    return this.request<Application>('GET', `/applications/${id}`);
  }

  async createApplication(data: {
    job_id: string;
    application_method: 'manual' | 'automated';
    notes?: string;
  }): Promise<Application> {
    return this.request<Application>('POST', '/applications', data);
  }

  async updateApplication(id: string, data: {
    status?: string;
    notes?: string;
    follow_up_date?: string;
  }): Promise<Application> {
    return this.request<Application>('PUT', `/applications/${id}`, data);
  }

  async withdrawApplication(id: string, reason: string): Promise<Application> {
    return this.request<Application>('POST', `/applications/${id}/withdraw`, { reason });
  }

  async getApplicationStatistics(): Promise<any> {
    return this.request<any>('GET', '/applications/statistics');
  }

  // Document endpoints
  async getDocuments(): Promise<Document[]> {
    return this.request<Document[]>('GET', '/documents');
  }

  async createDocument(data: {
    document_type: 'resume' | 'cover_letter';
    title: string;
    content: string;
    is_default?: boolean;
  }): Promise<Document> {
    return this.request<Document>('POST', '/documents', data);
  }

  async updateDocument(id: string, data: Partial<Document>): Promise<Document> {
    return this.request<Document>('PUT', `/documents/${id}`, data);
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request<void>('DELETE', `/documents/${id}`);
  }

  async generateResume(jobId: string): Promise<Document> {
    return this.request<Document>('POST', `/documents/generate/resume`, { job_id: jobId });
  }

  async generateCoverLetter(jobId: string): Promise<Document> {
    return this.request<Document>('POST', `/documents/generate/cover-letter`, { job_id: jobId });
  }
}

export const apiService = new ApiService();
EOF

echo "🎣 Creating React hooks..."

# Create useAuth hook
cat > src/hooks/useAuth.ts << 'EOF'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { getUserData, isAuthenticated, removeAuthToken, setUserData } from '../utils/auth';
import type { LoginRequest, RegisterRequest, User } from '../types/api';
import { toast } from 'react-hot-toast';

export const useAuth = () => {
  const queryClient = useQueryClient();

  const loginMutation = useMutation({
    mutationFn: (credentials: LoginRequest) => apiService.login(credentials),
    onSuccess: (data) => {
      setUserData(data.user);
      queryClient.setQueryData(['user'], data.user);
      toast.success('Login successful!');
    },
    onError: () => {
      toast.error('Login failed. Please check your credentials.');
    },
  });

  const registerMutation = useMutation({
    mutationFn: (userData: RegisterRequest) => apiService.register(userData),
    onSuccess: () => {
      toast.success('Registration successful! Please login.');
    },
    onError: () => {
      toast.error('Registration failed. Please try again.');
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => apiService.logout(),
    onSuccess: () => {
      queryClient.clear();
      toast.success('Logged out successfully!');
    },
    onError: () => {
      // Still remove local data even if server logout fails
      removeAuthToken();
      queryClient.clear();
    },
  });

  const { data: user, isLoading: isLoadingUser } = useQuery({
    queryKey: ['user'],
    queryFn: () => apiService.getUserProfile(),
    enabled: isAuthenticated(),
    initialData: getUserData(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    user,
    isLoadingUser,
    isAuthenticated: isAuthenticated(),
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    logout: logoutMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
};
EOF

# Create useApplications hook
cat > src/hooks/useApplications.ts << 'EOF'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { toast } from 'react-hot-toast';

export const useApplications = (params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery({
    queryKey: ['applications', params],
    queryFn: () => apiService.getApplications(params),
  });
};

export const useApplication = (id: string) => {
  return useQuery({
    queryKey: ['application', id],
    queryFn: () => apiService.getApplication(id),
    enabled: !!id,
  });
};

export const useCreateApplication = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      job_id: string;
      application_method: 'manual' | 'automated';
      notes?: string;
    }) => apiService.createApplication(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      toast.success('Application submitted successfully!');
    },
    onError: () => {
      toast.error('Failed to submit application.');
    },
  });
};

export const useUpdateApplication = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: {
      id: string;
      data: {
        status?: string;
        notes?: string;
        follow_up_date?: string;
      };
    }) => apiService.updateApplication(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      toast.success('Application updated successfully!');
    },
    onError: () => {
      toast.error('Failed to update application.');
    },
  });
};

export const useApplicationStatistics = () => {
  return useQuery({
    queryKey: ['application-statistics'],
    queryFn: () => apiService.getApplicationStatistics(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
EOF

# Create useJobs hook
cat > src/hooks/useJobs.ts << 'EOF'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { toast } from 'react-hot-toast';

export const useJobs = (searchParams?: {
  query?: string;
  location?: string;
  job_type?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery({
    queryKey: ['jobs', searchParams],
    queryFn: () => apiService.searchJobs(searchParams || {}),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

export const useJob = (id: string) => {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => apiService.getJob(id),
    enabled: !!id,
  });
};

export const useSavedJobs = () => {
  return useQuery({
    queryKey: ['saved-jobs'],
    queryFn: () => apiService.getSavedJobs(),
  });
};

export const useSaveJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiService.saveJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-jobs'] });
      toast.success('Job saved successfully!');
    },
    onError: () => {
      toast.error('Failed to save job.');
    },
  });
};

export const useUnsaveJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => apiService.unsaveJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-jobs'] });
      toast.success('Job removed from saved list.');
    },
    onError: () => {
      toast.error('Failed to remove job.');
    },
  });
};
EOF

echo "📱 Creating React Query provider..."
cat > src/context/QueryProvider.tsx << 'EOF'
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, type ReactNode } from 'react';

interface QueryProviderProps {
  children: ReactNode;
}

export const QueryProvider = ({ children }: QueryProviderProps) => {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 60 * 1000, // 1 minute
          retry: (failureCount, error: any) => {
            // Don't retry on auth errors
            if (error?.response?.status === 401 || error?.response?.status === 403) {
              return false;
            }
            return failureCount < 3;
          },
        },
        mutations: {
          retry: 1,
        },
      },
    })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};
EOF

echo "🌐 Creating authentication context..."
cat > src/context/AuthContext.tsx << 'EOF'
'use client';

import { createContext, useContext, type ReactNode } from 'react';
import { useAuth as useAuthHook } from '../hooks/useAuth';

interface AuthContextType {
  user: any;
  isLoadingUser: boolean;
  isAuthenticated: boolean;
  login: (credentials: any) => void;
  register: (userData: any) => void;
  logout: () => void;
  isLoggingIn: boolean;
  isRegistering: boolean;
  isLoggingOut: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const auth = useAuthHook();

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
EOF

echo "🔧 Creating common components..."

# Create Loading component
cat > src/components/common/Loading.tsx << 'EOF'
interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export const Loading = ({ size = 'md', text = 'Loading...' }: LoadingProps) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex items-center justify-center p-4">
      <div className="animate-spin">
        <div className={`border-4 border-gray-300 border-t-blue-600 rounded-full ${sizeClasses[size]}`} />
      </div>
      {text && <span className="ml-2 text-gray-600">{text}</span>}
    </div>
  );
};
EOF

# Create Error component
cat > src/components/common/ErrorMessage.tsx << 'EOF'
interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage = ({ message, onRetry }: ErrorMessageProps) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="text-red-600 mb-4">
        <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Something went wrong</h3>
      <p className="text-gray-600 mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
};
EOF

echo "🎨 Creating app layout..."
cat > src/app/layout.tsx << 'EOF'
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import { QueryProvider } from '../context/QueryProvider';
import { AuthProvider } from '../context/AuthContext';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Job Automation System',
  description: 'AI-powered job application automation platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <QueryProvider>
          <AuthProvider>
            <div className="min-h-screen bg-gray-50">
              {children}
            </div>
            <Toaster position="top-right" />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
EOF

echo "🎨 Creating global CSS..."
cat > src/app/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: system-ui, sans-serif;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
EOF

echo "📊 Creating dashboard page..."
cat > src/app/dashboard/page.tsx << 'EOF'
'use client';

import { useAuth } from '../../context/AuthContext';
import { useApplications } from '../../hooks/useApplications';
import { useApplicationStatistics } from '../../hooks/useApplications';
import { Loading } from '../../components/common/Loading';
import { ErrorMessage } from '../../components/common/ErrorMessage';

export default function DashboardPage() {
  const { user, isLoadingUser } = useAuth();
  const { data: applications, isLoading: isLoadingApplications, error: applicationsError, refetch: refetchApplications } = useApplications();
  const { data: statistics, isLoading: isLoadingStats } = useApplicationStatistics();

  if (isLoadingUser) {
    return <Loading text="Loading user data..." />;
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Welcome to Job Automation System</h1>
          <p className="text-gray-600 mb-8">Please log in to view your dashboard.</p>
          <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user.full_name}!</h1>
        <p className="text-gray-600 mt-2">Here's an overview of your job application progress.</p>
      </header>

      {/* Statistics Cards */}
      {isLoadingStats ? (
        <Loading text="Loading statistics..." />
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900">Total Applications</h3>
            <p className="text-3xl font-bold text-blue-600">{statistics.total_applications || 0}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900">Response Rate</h3>
            <p className="text-3xl font-bold text-green-600">{statistics.response_rate || 0}%</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900">Interviews</h3>
            <p className="text-3xl font-bold text-purple-600">{statistics.interview_count || 0}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900">Success Rate</h3>
            <p className="text-3xl font-bold text-orange-600">{statistics.success_rate || 0}%</p>
          </div>
        </div>
      ) : null}

      {/* Recent Applications */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Recent Applications</h2>
        </div>
        <div className="p-6">
          {isLoadingApplications ? (
            <Loading text="Loading applications..." />
          ) : applicationsError ? (
            <ErrorMessage 
              message="Failed to load applications. Please try again." 
              onRetry={() => refetchApplications()}
            />
          ) : applications?.data?.length ? (
            <div className="space-y-4">
              {applications.data.slice(0, 5).map((application) => (
                <div key={application.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-gray-900">{application.job.title}</h3>
                      <p className="text-gray-600">{application.job.company}</p>
                      <p className="text-sm text-gray-500">Applied: {new Date(application.applied_at).toLocaleDateString()}</p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      application.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                      application.status === 'interview_scheduled' ? 'bg-blue-100 text-blue-800' :
                      application.status === 'offer_received' ? 'bg-green-100 text-green-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {application.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No applications yet. Start by searching for jobs!</p>
          )}
        </div>
      </div>
    </div>
  );
}
EOF

echo "⚙️ Creating configuration files..."

# Create or update Next.js config
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
EOF

# Create environment variables
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=Job Automation System
NODE_ENV=development
EOF

# Update Tailwind config if it exists
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

echo "✅ Frontend integration setup complete!"
echo ""
echo "📊 Summary of what was created:"
echo "   📁 Directory structure:"
echo "      • src/services/ - API service layer"
echo "      • src/types/ - TypeScript interfaces"
echo "      • src/hooks/ - React hooks for data fetching"
echo "      • src/utils/ - Authentication utilities"
echo "      • src/context/ - React context providers"
echo "      • src/components/common/ - Reusable components"
echo "      • src/app/ - Next.js app directory"
echo ""
echo "   📝 Files created:"
echo "      • API types and interfaces (src/types/api.ts)"
echo "      • Complete API service (src/services/api.ts)"
echo "      • Authentication utilities (src/utils/auth.ts)"
echo "      • React hooks for auth, jobs, applications"
echo "      • React Query and Auth context providers"
echo "      • Loading and error components"
echo "      • App layout with providers"
echo "      • Dashboard page with API integration"
echo "      • Configuration files (next.config.js, .env.local)"
echo ""
echo "🔧 Next steps:"
echo "   1. Start the development server: npm run dev"
echo "   2. Navigate to http://localhost:3000"
echo "   3. Check /dashboard to see the integration in action"
echo "   4. Make sure your backend is running on port 8000"
echo ""
echo "🌐 Your frontend is now fully integrated with the backend API!"