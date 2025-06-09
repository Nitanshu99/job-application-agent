import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import {
  User,
  UserProfile,
  UserCreate,
  UserUpdate,
  Token,
  LoginCredentials,
  Job,
  JobSearchFilters,
  Application,
  ApplicationCreate,
  ApplicationUpdate,
  Document,
  DocumentCreate,
  JobPortal,
  JobPortalCreate,
  DashboardStats,
  ApplicationStats,
  AIProcessingStatus,
  DuplicateCheck,
  PaginatedResponse,
  ApiResponse
} from '../types';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_VERSION = '/api/v1';

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}${API_VERSION}`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.logout();
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage on initialization
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  setToken(token: string): void {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  logout(): void {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }

  // Authentication endpoints
  async login(credentials: LoginCredentials): Promise<Token> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await this.client.post<Token>('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(userData: UserCreate): Promise<User> {
    const response = await this.client.post<User>('/auth/register', userData);
    return response.data;
  }

  async refreshToken(): Promise<Token> {
    const response = await this.client.post<Token>('/auth/refresh');
    this.setToken(response.data.access_token);
    return response.data;
  }

  // User endpoints
  async getCurrentUser(): Promise<UserProfile> {
    const response = await this.client.get<UserProfile>('/users/profile');
    return response.data;
  }

  async updateProfile(userData: UserUpdate): Promise<UserProfile> {
    const response = await this.client.put<UserProfile>('/users/profile', userData);
    return response.data;
  }

  async getUserStats(): Promise<DashboardStats> {
    const response = await this.client.get<DashboardStats>('/users/stats');
    return response.data;
  }

  // Job endpoints
  async searchJobs(filters: JobSearchFilters = {}, page = 1, perPage = 20): Promise<PaginatedResponse<Job>> {
    const params = { ...filters, page, per_page: perPage };
    const response = await this.client.get<PaginatedResponse<Job>>('/jobs/search', { params });
    return response.data;
  }

  async getJob(jobId: string): Promise<Job> {
    const response = await this.client.get<Job>(`/jobs/${jobId}`);
    return response.data;
  }

  async analyzeJob(jobId: string): Promise<{ match_score: number; analysis: string }> {
    const response = await this.client.post(`/jobs/${jobId}/analyze`);
    return response.data;
  }

  async getJobRecommendations(): Promise<Job[]> {
    const response = await this.client.get<Job[]>('/jobs/recommendations');
    return response.data;
  }

  // Application endpoints
  async getApplications(page = 1, perPage = 20): Promise<PaginatedResponse<Application>> {
    const params = { page, per_page: perPage };
    const response = await this.client.get<PaginatedResponse<Application>>('/applications', { params });
    return response.data;
  }

  async getApplication(applicationId: string): Promise<Application> {
    const response = await this.client.get<Application>(`/applications/${applicationId}`);
    return response.data;
  }

  async createApplication(applicationData: ApplicationCreate): Promise<Application> {
    const response = await this.client.post<Application>('/applications', applicationData);
    return response.data;
  }

  async updateApplication(applicationId: string, updates: ApplicationUpdate): Promise<Application> {
    const response = await this.client.put<Application>(`/applications/${applicationId}`, updates);
    return response.data;
  }

  async deleteApplication(applicationId: string): Promise<void> {
    await this.client.delete(`/applications/${applicationId}`);
  }

  async checkDuplicate(jobId: string): Promise<DuplicateCheck> {
    const response = await this.client.post<DuplicateCheck>('/applications/check-duplicate', { job_id: jobId });
    return response.data;
  }

  async getApplicationStats(): Promise<ApplicationStats> {
    const response = await this.client.get<ApplicationStats>('/applications/statistics');
    return response.data;
  }

  async applyToJob(jobId: string, options: { 
    generateResume?: boolean; 
    generateCoverLetter?: boolean;
    resumeId?: string;
    coverLetterId?: string;
  }): Promise<Application> {
    const response = await this.client.post<Application>(`/jobs/${jobId}/apply`, options);
    return response.data;
  }

  // Document endpoints
  async getDocuments(): Promise<Document[]> {
    const response = await this.client.get<Document[]>('/documents');
    return response.data;
  }

  async getDocument(documentId: string): Promise<Document> {
    const response = await this.client.get<Document>(`/documents/${documentId}`);
    return response.data;
  }

  async createDocument(documentData: DocumentCreate): Promise<Document> {
    const response = await this.client.post<Document>('/documents', documentData);
    return response.data;
  }

  async generateResume(options: {
    jobId?: string;
    jobDescription?: string;
    template?: string;
    skillsToHighlight?: string[];
  }): Promise<Document> {
    const response = await this.client.post<Document>('/documents/resume', options);
    return response.data;
  }

  async generateCoverLetter(options: {
    jobId?: string;
    jobDescription?: string;
    template?: string;
  }): Promise<Document> {
    const response = await this.client.post<Document>('/documents/cover-letter', options);
    return response.data;
  }

  async updateDocument(documentId: string, content: string): Promise<Document> {
    const response = await this.client.put<Document>(`/documents/${documentId}`, { content });
    return response.data;
  }

  async deleteDocument(documentId: string): Promise<void> {
    await this.client.delete(`/documents/${documentId}`);
  }

  // Job Portal endpoints
  async getJobPortals(): Promise<JobPortal[]> {
    const response = await this.client.get<JobPortal[]>('/portals');
    return response.data;
  }

  async createJobPortal(portalData: JobPortalCreate): Promise<JobPortal> {
    const response = await this.client.post<JobPortal>('/portals', portalData);
    return response.data;
  }

  async updateJobPortal(portalId: string, updates: Partial<JobPortalCreate>): Promise<JobPortal> {
    const response = await this.client.put<JobPortal>(`/portals/${portalId}`, updates);
    return response.data;
  }

  async deleteJobPortal(portalId: string): Promise<void> {
    await this.client.delete(`/portals/${portalId}`);
  }

  async syncJobPortal(portalId: string): Promise<{ jobs_found: number; message: string }> {
    const response = await this.client.post(`/portals/${portalId}/sync`);
    return response.data;
  }

  // AI Status endpoints
  async getAIStatus(): Promise<AIProcessingStatus> {
    const response = await this.client.get<AIProcessingStatus>('/ai/status');
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; message: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
