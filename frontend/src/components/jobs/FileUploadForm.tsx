import { useState, ChangeEvent, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, AlertIcon, Box, FormControl, FormErrorMessage, FormLabel, Stack, Text } from '@chakra-ui/react';
import { GradientButton } from '../ui/GradientButton';
import { useSubmitFile } from '../../hooks/useJobs';

export function FileUploadForm(): JSX.Element {
  const navigate = useNavigate();
  const submitFile = useSubmitFile();

  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | undefined>(undefined);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setValidationError(undefined);
    setFile(e.target.files?.[0] ?? null);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setValidationError(undefined);

    if (!file) {
      setValidationError('Please choose a video file to upload');
      return;
    }

    try {
      const job = await submitFile.mutateAsync(file);
      navigate(`/jobs/${job.id}`);
    } catch {
      // handled by submitFile.isError below
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack spacing={4}>
        {submitFile.isError && (
          <Alert status="error" borderRadius="lg">
            <AlertIcon />
            Failed to upload the video. Please try again.
          </Alert>
        )}

        <FormControl isInvalid={!!validationError}>
          <FormLabel fontSize="sm" fontWeight="medium">
            Video file
          </FormLabel>
          <Box
            p={4}
            borderRadius="xl"
            border="2px dashed"
            borderColor={validationError ? 'red.500' : 'gray.200'}
          >
            <input type="file" accept="video/*" onChange={handleFileChange} />
            {file && (
              <Text fontSize="sm" mt={2} color="gray.600">
                Selected: {file.name}
              </Text>
            )}
          </Box>
          {validationError && <FormErrorMessage>{validationError}</FormErrorMessage>}
        </FormControl>

        <GradientButton
          type="submit"
          disabled={submitFile.isPending}
          opacity={submitFile.isPending ? 0.7 : 1}
          w="full"
        >
          {submitFile.isPending ? 'Uploading...' : 'Upload Video'}
        </GradientButton>
      </Stack>
    </form>
  );
}
