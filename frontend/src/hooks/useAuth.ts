import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { apiService } from '../services/api';
import { User, LoginCredentials, UserCreate } from '../types';
import toast from 'react-hot-toast';

interface AuthState {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
}

export const useAuth = () => {
  const router = useRouter();
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    loading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setAuthState({ user: null, loading: false, isAuthenticated: false });
        return;
      }

      const user = await apiService.getCurrentUser();
      setAuthState({ user, loading: false, isAuthenticated: true });
    } catch (error) {
      // Token might be expired or invalid
      localStorage.removeItem('access_token');
      setAuthState({ user: null, loading: false, isAuthenticated: false });
    }
  };

  const login = async (credentials: LoginCredentials) => {
    try {
      setAuthState(prev => ({ ...prev, loading: true }));
      
      const tokenResponse = await apiService.login(credentials);
      const user = await apiService.getCurrentUser();
      
      setAuthState({ user, loading: false, isAuthenticated: true });
      toast.success('Successfully logged in!');
      
      // Redirect to dashboard or intended page
      const redirectTo = router.query.redirect as string || '/dashboard';
      router.push(redirectTo);
      
      return { success: true };
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, loading: false }));
      const errorMessage = error.response?.data?.detail || 'Login failed';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const register = async (userData: UserCreate) => {
    try {
      setAuthState(prev => ({ ...prev, loading: true }));
      
      await apiService.register(userData);
      
      // Auto-login after registration
      const loginResult = await login({
        username: userData.email,
        password: userData.password,
      });
      
      if (loginResult.success) {
        toast.success('Account created successfully!');
      }
      
      return loginResult;
    } catch (error: any) {
      setAuthState(prev => ({ ...prev, loading: false }));
      const errorMessage = error.response?.data?.detail || 'Registration failed';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    apiService.logout();
    setAuthState({ user: null, loading: false, isAuthenticated: false });
    toast.success('Logged out successfully');
    router.push('/login');
  };

  const updateProfile = async (updates: Partial<User>) => {
    try {
      const updatedUser = await apiService.updateProfile(updates);
      setAuthState(prev => ({ ...prev, user: updatedUser }));
      toast.success('Profile updated successfully');
      return { success: true, user: updatedUser };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update profile';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  return {
    ...authState,
    login,
    register,
    logout,
    updateProfile,
    checkAuthStatus,
  };
};
