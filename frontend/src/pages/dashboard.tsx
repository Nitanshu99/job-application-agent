import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, StatCard } from '../components/ui/Card';
import { Navbar } from '../components/layout/Navbar';
import { apiService } from '../services/api';
import { DashboardStats, Application, User, AIProcessingStatus } from '../types';
import { format } from 'date-fns';

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentApplications, setRecentApplications] = useState<Application[]>([]);
  const [aiStatus, setAiStatus] = useState<AIProcessingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    // Set up polling for AI status
    const interval = setInterval(loadAIStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [userResponse, statsResponse, applicationsResponse] = await Promise.all([
        apiService.getCurrentUser(),
        apiService.getUserStats(),
        apiService.getApplications(1, 5), // Get recent 5 applications
      ]);

      setUser(userResponse);
      setStats(statsResponse);
      setRecentApplications(applicationsResponse.data);
      await loadAIStatus();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load dashboard data');
      if (err.response?.status === 401) {
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadAIStatus = async () => {
    try {
      const status = await apiService.getAIStatus();
      setAiStatus(status);
    } catch (err) {
      console.error('Failed to load AI status:', err);
    }
  };

  const handleLogout = () => {
    apiService.logout();
    router.push('/login');
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { bg: 'bg-orange-100', text: 'text-orange-600', label: 'Pending' },
      applied: { bg: 'bg-blue-100', text: 'text-blue-600', label: 'Applied' },
      interview: { bg: 'bg-green-100', text: 'text-green-600', label: 'Interview' },
      offer: { bg: 'bg-purple-100', text: 'text-purple-600', label: 'Offer' },
      rejected: { bg: 'bg-red-100', text: 'text-red-600', label: 'Rejected' },
      withdrawn: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Withdrawn' },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;

    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const getAIStatusIcon = (status: string) => {
    switch (status) {
      case 'ready': return '✓';
      case 'processing': return '⟳';
      case 'error': return '⚠';
      default: return '•';
    }
  };

  const getAIStatusClass = (status: string) => {
    switch (status) {
      case 'ready': return 'bg-green-50 text-green-600';
      case 'processing': return 'bg-blue-50 text-blue-600';
      case 'error': return 'bg-red-50 text-red-600';
      default: return 'bg-gray-50 text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar user={user} onLogout={handleLogout} />
        <div className="flex items-center justify-center h-96">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar user={user} onLogout={handleLogout} />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={loadDashboardData}>Try Again</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar user={user} onLogout={handleLogout} />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Welcome back, {user?.full_name}!</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Applications"
            value={stats?.total_applications || 0}
            change={{
              value: `+${stats?.applications_this_week || 0} this week`,
              trend: 'up'
            }}
          />
          <StatCard
            title="Interviews Scheduled"
            value={stats?.interviews_scheduled || 0}
            change={{
              value: `${stats?.response_rate || 0}% response rate`,
              trend: 'up'
            }}
          />
          <StatCard
            title="Offers Received"
            value={stats?.offers_received || 0}
            change={{
              value: `${stats?.success_rate || 0}% success rate`,
              trend: 'up'
            }}
          />
          <StatCard
            title="Avg Response Time"
            value={`${stats?.average_response_time || 0}d`}
            change={{
              value: 'Industry avg: 7d',
              trend: 'neutral'
            }}
          />
        </div>

        {/* AI Processing Status */}
        <Card className="mb-8">
          <CardHeader title="AI Processing Status" />
          <div className="space-y-4">
            {aiStatus && (
              <>
                <div className={`flex items-center gap-3 p-4 rounded-lg ${getAIStatusClass(aiStatus.phi3_status)}`}>
                  <span className="text-lg">{getAIStatusIcon(aiStatus.phi3_status)}</span>
                  <span className="font-medium">Phi-3 Mini: Document generation {aiStatus.phi3_status}</span>
                </div>
                <div className={`flex items-center gap-3 p-4 rounded-lg ${getAIStatusClass(aiStatus.gemma_status)}`}>
                  <span className="text-lg">{getAIStatusIcon(aiStatus.gemma_status)}</span>
                  <span className="font-medium">Gemma 7B: Job matching {aiStatus.gemma_status}</span>
                </div>
                <div className={`flex items-center gap-3 p-4 rounded-lg ${getAIStatusClass(aiStatus.mistral_status)}`}>
                  <span className="text-lg">{getAIStatusIcon(aiStatus.mistral_status)}</span>
                  <span className="font-medium">
                    Mistral 7B: Application processing {aiStatus.mistral_status}
                    {aiStatus.current_task && ` - ${aiStatus.current_task}`}
                  </span>
                </div>
                {aiStatus.progress && (
                  <div className="mt-4">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${aiStatus.progress}%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-gray-600 mt-2">{aiStatus.progress}% complete</p>
                  </div>
                )}
              </>
            )}
          </div>
        </Card>

        {/* Recent Applications */}
        <Card className="mb-8">
          <CardHeader 
            title="Recent Applications" 
            action={
              <Button onClick={() => router.push('/applications')} size="small">
                View All
              </Button>
            }
          />
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 text-sm font-medium text-gray-700">Position</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-700">Company</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-700">Applied Date</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-700">Status</th>
                  <th className="text-left py-3 text-sm font-medium text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentApplications.map((application) => (
                  <tr key={application.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4">
                      <div>
                        <p className="font-medium text-gray-900">{application.job.title}</p>
                        {application.application_method === 'auto_ai' && (
                          <p className="text-xs text-blue-600">Auto-applied via AI</p>
                        )}
                      </div>
                    </td>
                    <td className="py-4 text-gray-700">{application.job.company}</td>
                    <td className="py-4 text-gray-700">
                      {format(new Date(application.applied_date), 'MMM d, yyyy')}
                    </td>
                    <td className="py-4">{getStatusBadge(application.status)}</td>
                    <td className="py-4">
                      <Button 
                        size="small" 
                        variant="secondary"
                        onClick={() => router.push(`/applications/${application.id}`)}
                      >
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader title="Quick Actions" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Button 
              onClick={() => router.push('/jobs')}
              className="flex flex-col items-center py-6 h-auto"
              variant="primary"
            >
              <span className="text-2xl mb-2">🔍</span>
              <span>Search Jobs</span>
            </Button>
            <Button 
              onClick={() => router.push('/documents?generate=resume')}
              className="flex flex-col items-center py-6 h-auto"
              variant="success"
            >
              <span className="text-2xl mb-2">📄</span>
              <span>Generate Resume</span>
            </Button>
            <Button 
              onClick={() => router.push('/portals')}
              className="flex flex-col items-center py-6 h-auto"
              variant="secondary"
            >
              <span className="text-2xl mb-2">➕</span>
              <span>Add Job Portal</span>
            </Button>
            <Button 
              onClick={() => router.push('/applications?view=analytics')}
              className="flex flex-col items-center py-6 h-auto"
              variant="warning"
            >
              <span className="text-2xl mb-2">📊</span>
              <span>View Analytics</span>
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}
