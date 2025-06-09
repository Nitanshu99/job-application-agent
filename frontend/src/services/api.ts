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
