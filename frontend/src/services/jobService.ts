import api from './api';
import type { VideoJob } from '../types';

export async function submitUrl(youtubeUrl: string): Promise<VideoJob> {
  const form = new FormData();
  form.append('youtube_url', youtubeUrl);
  const { data } = await api.post<VideoJob>('/jobs/', form);
  return data;
}

export async function submitFile(file: File): Promise<VideoJob> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<VideoJob>('/jobs/', form);
  return data;
}

export async function listJobs(): Promise<VideoJob[]> {
  const { data } = await api.get<VideoJob[]>('/jobs/');
  return data;
}

export async function getJob(id: number): Promise<VideoJob> {
  const { data } = await api.get<VideoJob>(`/jobs/${id}`);
  return data;
}

export async function deleteJob(id: number): Promise<void> {
  await api.delete(`/jobs/${id}`);
}

/**
 * Returns the full URL string for the download endpoint. NOTE: a plain
 * <video src> or <a href> pointed at this URL will NOT carry the axios
 * auth header (the browser makes that request directly, bypassing our
 * interceptor), so for MVP this only works if the endpoint is reachable
 * without auth. Prefer `downloadJobBlob` below, which respects auth,
 * for both video playback and downloads.
 */
export function getDownloadUrl(id: number): string {
  return `${api.defaults.baseURL}/jobs/${id}/download`;
}

/**
 * Fetches the rendered video as a Blob via the authenticated axios
 * client. Use `URL.createObjectURL(blob)` for <video> playback or to
 * trigger a browser download.
 */
export async function downloadJobBlob(id: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/jobs/${id}/download`, {
    responseType: 'blob',
  });
  return data;
}
