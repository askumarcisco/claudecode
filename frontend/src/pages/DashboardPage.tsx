import { Center, Heading, Link, Spinner, Stack, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { GradientButton } from '../components/ui/GradientButton';
import { AnimatedList } from '../components/ui/AnimatedList';
import { UrlSubmitForm } from '../components/jobs/UrlSubmitForm';
import { JobStatusCard } from '../components/jobs/JobStatusCard';
import { useAuth } from '../hooks/useAuth';
import { useJobs } from '../hooks/useJobs';

const RECENT_JOBS_LIMIT = 5;

export default function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  const { data: jobs, isLoading, isError } = useJobs();

  const displayName = user?.full_name || user?.email || 'there';
  const recentJobs = (jobs ?? []).slice(0, RECENT_JOBS_LIMIT);

  return (
    <PageWrapper>
      <MeshBackground />
      <Stack spacing={8} maxW="3xl" mx="auto" px={4} py={12}>
        <Heading size="lg">Welcome back, {displayName}</Heading>

        <GlassCard>
          <Stack spacing={4}>
            <Heading size="md">Submit a video</Heading>
            <UrlSubmitForm />
            <Link as={RouterLink} to="/submit" fontSize="sm" color="brand.500" fontWeight="semibold" alignSelf="flex-start">
              or upload a file instead →
            </Link>
          </Stack>
        </GlassCard>

        <Stack spacing={4}>
          <Stack direction="row" justify="space-between" align="center">
            <Heading size="md">Recent jobs</Heading>
            <GradientButton as={RouterLink} to="/jobs" px={4} py={2} fontSize="sm">
              View all →
            </GradientButton>
          </Stack>

          {isLoading && (
            <Center py={8}>
              <Spinner size="lg" color="brand.500" thickness="3px" />
            </Center>
          )}

          {isError && (
            <Text color="red.500" fontSize="sm">
              Could not load your recent jobs. Please try again later.
            </Text>
          )}

          {!isLoading && !isError && recentJobs.length === 0 && (
            <GlassCard>
              <Text color="gray.600">No videos yet — paste a YouTube URL above to get started.</Text>
            </GlassCard>
          )}

          {!isLoading && !isError && recentJobs.length > 0 && (
            <AnimatedList>
              {recentJobs.map((job) => (
                <JobStatusCard key={job.id} job={job} />
              ))}
            </AnimatedList>
          )}
        </Stack>
      </Stack>
    </PageWrapper>
  );
}
