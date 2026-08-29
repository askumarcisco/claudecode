import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, AlertIcon, Stack } from '@chakra-ui/react';
import { AnimatedInput } from '../ui/AnimatedInput';
import { GradientButton } from '../ui/GradientButton';
import { useSubmitUrl } from '../../hooks/useJobs';

const URL_REGEX = /^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\/.+/i;

export function UrlSubmitForm(): JSX.Element {
  const navigate = useNavigate();
  const submitUrl = useSubmitUrl();

  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [validationError, setValidationError] = useState<string | undefined>(undefined);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setValidationError(undefined);

    if (!youtubeUrl.trim()) {
      setValidationError('A YouTube URL is required');
      return;
    }
    if (!URL_REGEX.test(youtubeUrl.trim())) {
      setValidationError('Enter a valid YouTube URL');
      return;
    }

    try {
      const job = await submitUrl.mutateAsync(youtubeUrl.trim());
      navigate(`/jobs/${job.id}`);
    } catch {
      // handled by submitUrl.isError below
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack spacing={4}>
        {submitUrl.isError && (
          <Alert status="error" borderRadius="lg">
            <AlertIcon />
            Failed to submit the video. Please check the URL and try again.
          </Alert>
        )}

        <AnimatedInput
          label="YouTube URL"
          type="url"
          value={youtubeUrl}
          onChange={(e) => setYoutubeUrl(e.target.value)}
          error={validationError}
          placeholder="https://www.youtube.com/watch?v=..."
          autoComplete="off"
        />

        <GradientButton
          type="submit"
          disabled={submitUrl.isPending}
          opacity={submitUrl.isPending ? 0.7 : 1}
          w="full"
        >
          {submitUrl.isPending ? 'Submitting...' : 'Submit Video'}
        </GradientButton>
      </Stack>
    </form>
  );
}
