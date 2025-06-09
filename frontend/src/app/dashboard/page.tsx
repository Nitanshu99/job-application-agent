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
