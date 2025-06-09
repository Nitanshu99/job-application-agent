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
