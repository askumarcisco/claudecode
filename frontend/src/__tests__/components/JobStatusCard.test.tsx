import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import { JobStatusCard } from '../../components/jobs/JobStatusCard';
import theme from '../../theme';
import type { VideoJob } from '../../types';

function renderCard(job: VideoJob) {
  return render(
    <ChakraProvider theme={theme}>
      <MemoryRouter>
        <JobStatusCard job={job} />
      </MemoryRouter>
    </ChakraProvider>
  );
}

const baseJob: VideoJob = {
  id: 1,
  user_id: 1,
  source_type: 'youtube_url',
  youtube_url: 'https://www.youtube.com/watch?v=abc123',
  uploaded_file_path: null,
  source_title: 'My Cool Video',
  source_duration_seconds: 120,
  status: 'queued',
  error_message: null,
  output_file_path: null,
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: null,
};

describe('JobStatusCard', () => {
  test('renders the source title and status badge', () => {
    renderCard(baseJob);
    expect(screen.getByText('My Cool Video')).toBeInTheDocument();
    expect(screen.getByText('queued')).toBeInTheDocument();
  });

  test('falls back to the youtube url when there is no title', () => {
    renderCard({ ...baseJob, source_title: null });
    expect(screen.getByText(baseJob.youtube_url as string)).toBeInTheDocument();
  });

  test('falls back to a generic job label when there is no title or url', () => {
    renderCard({ ...baseJob, source_title: null, youtube_url: null });
    expect(screen.getByText(`Job #${baseJob.id}`)).toBeInTheDocument();
  });

  test('shows a spinner while an in-progress status is active', () => {
    const { container } = renderCard({ ...baseJob, status: 'transcribing' });
    expect(screen.getByText('transcribing')).toBeInTheDocument();
    expect(container.querySelector('.chakra-spinner')).toBeInTheDocument();
  });

  test('does not show a spinner for a terminal status', () => {
    const { container } = renderCard({ ...baseJob, status: 'done' });
    expect(screen.getByText('done')).toBeInTheDocument();
    expect(container.querySelector('.chakra-spinner')).not.toBeInTheDocument();
  });

  test('links to the job detail page', () => {
    renderCard(baseJob);
    const link = screen.getByRole('link', { name: /view details/i });
    expect(link).toHaveAttribute('href', `/jobs/${baseJob.id}`);
  });
});
