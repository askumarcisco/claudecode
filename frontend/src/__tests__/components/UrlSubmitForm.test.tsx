import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { UrlSubmitForm } from '../../components/jobs/UrlSubmitForm';
import { useSubmitUrl } from '../../hooks/useJobs';
import theme from '../../theme';
import type { VideoJob } from '../../types';

vi.mock('../../hooks/useJobs', () => ({
  useSubmitUrl: vi.fn(),
}));

const mockedUseSubmitUrl = vi.mocked(useSubmitUrl);
const mockMutateAsync = vi.fn();

const sampleJob: VideoJob = {
  id: 42,
  user_id: 1,
  source_type: 'youtube_url',
  youtube_url: 'https://www.youtube.com/watch?v=abc123',
  uploaded_file_path: null,
  source_title: null,
  source_duration_seconds: null,
  status: 'queued',
  error_message: null,
  output_file_path: null,
  created_at: '2026-01-01T00:00:00.000Z',
  updated_at: null,
};

function mockHook(overrides: { isPending?: boolean; isError?: boolean } = {}) {
  mockedUseSubmitUrl.mockReturnValue({
    mutateAsync: mockMutateAsync,
    isPending: overrides.isPending ?? false,
    isError: overrides.isError ?? false,
  } as unknown as ReturnType<typeof useSubmitUrl>);
}

function renderForm() {
  return render(
    <ChakraProvider theme={theme}>
      <MemoryRouter initialEntries={['/submit']}>
        <Routes>
          <Route path="/submit" element={<UrlSubmitForm />} />
          <Route path="/jobs/:id" element={<div>Job Detail Page</div>} />
        </Routes>
      </MemoryRouter>
    </ChakraProvider>
  );
}

describe('UrlSubmitForm', () => {
  beforeEach(() => {
    mockMutateAsync.mockReset();
    mockHook();
  });

  test('renders the youtube url field and submit button', () => {
    renderForm();
    expect(screen.getByPlaceholderText(/https:\/\/www\.youtube\.com/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit video/i })).toBeInTheDocument();
  });

  test('shows a validation error when the field is empty', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: /submit video/i }));

    expect(await screen.findByText(/youtube url is required/i)).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  test('shows a validation error for a non-youtube url', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(
      screen.getByPlaceholderText(/https:\/\/www\.youtube\.com/i),
      'https://example.com/video'
    );
    await user.click(screen.getByRole('button', { name: /submit video/i }));

    expect(await screen.findByText(/enter a valid youtube url/i)).toBeInTheDocument();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  test('submits a valid url and navigates to the job detail page', async () => {
    mockMutateAsync.mockResolvedValueOnce(sampleJob);
    const user = userEvent.setup();
    renderForm();

    await user.type(
      screen.getByPlaceholderText(/https:\/\/www\.youtube\.com/i),
      'https://www.youtube.com/watch?v=abc123'
    );
    await user.click(screen.getByRole('button', { name: /submit video/i }));

    await waitFor(() =>
      expect(mockMutateAsync).toHaveBeenCalledWith('https://www.youtube.com/watch?v=abc123')
    );
    expect(await screen.findByText('Job Detail Page')).toBeInTheDocument();
  });

  test('disables the submit button while the mutation is pending', () => {
    mockHook({ isPending: true });
    renderForm();
    expect(screen.getByRole('button', { name: /submitting/i })).toBeDisabled();
  });

  test('shows an error alert when the mutation is in an error state', () => {
    mockHook({ isError: true });
    renderForm();
    expect(screen.getByText(/failed to submit the video/i)).toBeInTheDocument();
  });
});
