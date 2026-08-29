import { Badge, HStack, Link, Spinner, Stack, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { GlassCard } from '../ui/GlassCard';
import type { JobStatus, VideoJob } from '../../types';

const STATUS_COLOR: Record<JobStatus, string> = {
  queued: 'gray',
  downloading: 'blue',
  transcribing: 'blue',
  analyzing: 'blue',
  rendering: 'blue',
  done: 'green',
  failed: 'red',
};

const IN_PROGRESS_STATUSES: readonly JobStatus[] = ['downloading', 'transcribing', 'analyzing', 'rendering'];

interface JobStatusCardProps {
  job: VideoJob;
}

export function JobStatusCard({ job }: JobStatusCardProps): JSX.Element {
  const title = job.source_title ?? job.youtube_url ?? job.uploaded_file_path ?? `Job #${job.id}`;
  const isInProgress = IN_PROGRESS_STATUSES.includes(job.status);

  return (
    <GlassCard mb={4}>
      <Stack spacing={2}>
        <HStack justify="space-between" align="flex-start">
          <Text fontWeight="semibold" noOfLines={1}>
            {title}
          </Text>
          <Badge colorScheme={STATUS_COLOR[job.status]} borderRadius="full" px={3} py={1}>
            <HStack spacing={1}>
              {isInProgress && <Spinner size="xs" />}
              <Text as="span">{job.status}</Text>
            </HStack>
          </Badge>
        </HStack>

        {job.youtube_url && (
          <Text fontSize="sm" color="gray.600" noOfLines={1}>
            {job.youtube_url}
          </Text>
        )}

        <Text fontSize="xs" color="gray.500">
          Created {new Date(job.created_at).toLocaleString()}
        </Text>

        <Link as={RouterLink} to={`/jobs/${job.id}`} color="brand.500" fontWeight="semibold" fontSize="sm">
          View details
        </Link>
      </Stack>
    </GlassCard>
  );
}
