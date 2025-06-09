import { Navbar } from '../../components/layout/Navbar';
import { useAuth } from '../../hooks/useAuth';

export default function Documents() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar user={user} onLogout={logout} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Documents</h1>
        <div className="bg-white rounded-xl p-8 text-center">
          <p className="text-gray-600">Document generation coming soon...</p>
        </div>
      </main>
    </div>
  );
}
