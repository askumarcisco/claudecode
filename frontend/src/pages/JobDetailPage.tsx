import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, AlertIcon, Badge, Center, Container, Heading, Progress, Spinner, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { useJob } from '../hooks/useJobs';
import { downloadJobBlob } from '../services/jobService';
import type { JobStatus } from '../types';

const STATUS_ORDER: readonly JobStatus[] = [
  'queued',
  'downloading',
  'transcribing',
  'analyzing',
  'rendering',
  'done',
];

const STATUS_LABEL: Record<JobStatus, string> = {
  queued: 'Queued',
  downloading: 'Downloading source video',
  transcribing: 'Transcribing audio',
  analyzing: 'Analyzing best moments',
  rendering: 'Rendering output',
  done: 'Done',
  failed: 'Failed',
};

const STATUS_COLOR: Record<JobStatus, string> = {
  queued: 'gray',
  downloading: 'blue',
  transcribing: 'blue',
  analyzing: 'blue',
  rendering: 'blue',
  done: 'green',
  failed: 'red',
};

function progressForStatus(status: JobStatus): number {
  if (status === 'failed') return 100;
  const index = STATUS_ORDER.indexOf(status);
  if (index === -1) return 0;
  return ((index + 1) / STATUS_ORDER.length) * 100;
}

export default function JobDetailPage(): JSX.Element {
  const { id } = useParams<{ id: string }>();
  const jobId = Number(id);
  const { data: job, isLoading, isError } = useJob(jobId);

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);

  useEffect(() => {
    if (job?.status !== 'done') return;

    let objectUrl: string | null = null;
    let cancelled = false;

    downloadJobBlob(job.id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setVideoBlob(blob);
        setVideoUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setVideoError('Failed to load the rendered video.');
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [job?.status, job?.id]);

  const handleDownload = (): void => {
    if (!videoBlob || !job) return;
    const url = URL.createObjectURL(videoBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${job.source_title ?? `video-${job.id}`}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <PageWrapper>
      <MeshBackground />
      <Container maxW="2xl" py={12}>
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" color="brand.500" thickness="3px" />
          </Center>
        )}

        {isError && (
          <GlassCard>
            <Text color="red.500">Failed to load this job.</Text>
          </GlassCard>
        )}

        {job && (
          <GlassCard>
            <Stack spacing={5}>
              <Stack direction="row" justify="space-between" align="center">
                <Heading size="md">{job.source_title ?? job.youtube_url ?? `Job #${job.id}`}</Heading>
                <Badge colorScheme={STATUS_COLOR[job.status]} borderRadius="full" px={3} py={1}>
                  {job.status}
                </Badge>
              </Stack>

              <Stack spacing={2}>
                <Text fontSize="sm" color="gray.600">
                  {STATUS_LABEL[job.status]}
                </Text>
                <Progress
                  value={progressForStatus(job.status)}
                  colorScheme={job.status === 'failed' ? 'red' : 'purple'}
                  borderRadius="full"
                  size="sm"
                  hasStripe={job.status !== 'done' && job.status !== 'failed'}
                  isAnimated={job.status !== 'done' && job.status !== 'failed'}
                />
              </Stack>

              {job.status === 'failed' && (
                <Alert status="error" borderRadius="lg">
                  <AlertIcon />
                  {job.error_message ?? 'The job failed for an unknown reason.'}
                </Alert>
              )}

              {job.status === 'done' && (
                <Stack spacing={4}>
                  {videoError && (
                    <Alert status="error" borderRadius="lg">
                      <AlertIcon />
                      {videoError}
                    </Alert>
                  )}

                  {!videoUrl && !videoError && (
                    <Center py={6}>
                      <Spinner color="brand.500" />
                    </Center>
                  )}

                  {videoUrl && (
                    <>
                      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                      <video controls src={videoUrl} style={{ width: '100%', borderRadius: '1rem' }} />
                      <GradientButton onClick={handleDownload} w="full">
                        Download video
                      </GradientButton>
                    </>
                  )}
                </Stack>
              )}

              <Text fontSize="xs" color="gray.500">
                Created {new Date(job.created_at).toLocaleString()}
              </Text>
            </Stack>
          </GlassCard>
        )}
      </Container>
    </PageWrapper>
  );
}
