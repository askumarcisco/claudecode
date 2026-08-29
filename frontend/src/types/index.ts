export type JobStatus = 'queued' | 'downloading' | 'transcribing' | 'analyzing' | 'rendering' | 'done' | 'failed';
export type SourceType = 'youtube_url' | 'upload';

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface VideoJob {
  id: number;
  user_id: number;
  source_type: SourceType;
  youtube_url: string | null;
  uploaded_file_path: string | null;
  source_title: string | null;
  source_duration_seconds: number | null;
  status: JobStatus;
  error_message: string | null;
  output_file_path: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TranscriptSegment {
  id: number;
  job_id: number;
  start_time: number;
  end_time: number;
  text: string;
}

export interface SelectedMoment {
  id: number;
  job_id: number;
  start_time: number;
  end_time: number;
  reason: string | null;
}
