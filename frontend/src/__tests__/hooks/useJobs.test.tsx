import { describe, test, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { http, HttpResponse } from 'msw';
import { server } from '../setup';
import { useJobs, useJob, useSubmitUrl, useDeleteJob } from '../../hooks/useJobs';
import type { VideoJob } from '../../types';

const API_BASE = `${import.meta.env.VITE_API_URL}/api/v1`;

const sampleJob: VideoJob = {
  id: 1,
  user_id: 1,
  source_type: 'youtube_url',
  youtube_url: 'https://www.youtube.com/watch?v=abc123',
  uploaded_file_path: null,
  source_title: 'Sample Video',
  source_duration_seconds: 60,
  status: 'done',
  error_message: null,
  output_file_path: '/outputs/1.mp4',
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:05:00.000Z',
};

function createWrapper(): ({ children }: { children: ReactNode }) => JSX.Element {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useJobs', () => {
  test('fetches the list of jobs', async () => {
    server.use(http.get(`${API_BASE}/jobs/`, () => HttpResponse.json([sampleJob])));

    const { result } = renderHook(() => useJobs(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([sampleJob]);
  });

  test('surfaces an error when the request fails', async () => {
    server.use(
      http.get(`${API_BASE}/jobs/`, () => HttpResponse.json({ message: 'boom' }, { status: 500 }))
    );

    const { result } = renderHook(() => useJobs(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useJob', () => {
  test('fetches a single job by id', async () => {
    server.use(http.get(`${API_BASE}/jobs/1`, () => HttpResponse.json(sampleJob)));

    const { result } = renderHook(() => useJob(1), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe(1);
  });
});

describe('useSubmitUrl', () => {
  test('posts a youtube url and returns the created job', async () => {
    server.use(http.post(`${API_BASE}/jobs/`, () => HttpResponse.json(sampleJob, { status: 201 })));

    const { result } = renderHook(() => useSubmitUrl(), { wrapper: createWrapper() });

    result.current.mutate('https://www.youtube.com/watch?v=abc123');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(sampleJob);
  });
});

describe('useDeleteJob', () => {
  test('deletes a job', async () => {
    server.use(http.delete(`${API_BASE}/jobs/1`, () => new HttpResponse(null, { status: 204 })));

    const { result } = renderHook(() => useDeleteJob(), { wrapper: createWrapper() });

    result.current.mutate(1);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
