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
