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
