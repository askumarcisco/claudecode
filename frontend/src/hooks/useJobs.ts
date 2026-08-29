import { useMutation, useQuery, useQueryClient, type UseQueryResult, type UseMutationResult } from '@tanstack/react-query';
import * as jobService from '../services/jobService';
import type { VideoJob } from '../types';

const JOBS_KEY = ['jobs'] as const;
const jobKey = (id: number): readonly [string, number] => ['jobs', id] as const;

const TERMINAL_STATUSES: readonly VideoJob['status'][] = ['done', 'failed'];

export function useJobs(): UseQueryResult<VideoJob[], Error> {
  return useQuery({
    queryKey: JOBS_KEY,
    queryFn: jobService.listJobs,
    refetchInterval: 5000,
  });
}

export function useJob(id: number): UseQueryResult<VideoJob, Error> {
  return useQuery({
    queryKey: jobKey(id),
    queryFn: () => jobService.getJob(id),
    enabled: Number.isFinite(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.includes(status)) return false;
      return 5000;
    },
  });
}

export function useSubmitUrl(): UseMutationResult<VideoJob, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (youtubeUrl: string) => jobService.submitUrl(youtubeUrl),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}

export function useSubmitFile(): UseMutationResult<VideoJob, Error, File> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => jobService.submitFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}

export function useDeleteJob(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => jobService.deleteJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: JOBS_KEY });
    },
  });
}
