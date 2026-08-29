import { Center, Container, Heading, HStack, Spinner, Stack, Text } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GradientButton } from '../components/ui/GradientButton';
import { AnimatedList } from '../components/ui/AnimatedList';
import { GlassCard } from '../components/ui/GlassCard';
import { JobStatusCard } from '../components/jobs/JobStatusCard';
import { useJobs } from '../hooks/useJobs';

export default function JobsListPage(): JSX.Element {
  const { data: jobs, isLoading, isError } = useJobs();
  const navigate = useNavigate();

  return (
    <PageWrapper>
      <Container maxW="2xl" py={12}>
        <Stack spacing={6}>
          <HStack justify="space-between" align="center">
            <Heading size="lg" bgGradient="linear(to-r, brand.500, accent.500)" bgClip="text">
              Your videos
            </Heading>
            <GradientButton onClick={() => navigate('/submit')}>New submission</GradientButton>
          </HStack>

          {isLoading && (
            <Center py={12}>
              <Spinner size="xl" color="brand.500" thickness="3px" />
            </Center>
          )}

          {isError && (
            <GlassCard>
              <Text color="red.500">Failed to load your videos. Please try again later.</Text>
            </GlassCard>
          )}

          {!isLoading && !isError && jobs && jobs.length === 0 && (
            <GlassCard>
              <Stack spacing={4} align="center" py={8}>
                <Text color="gray.600">You haven&apos;t submitted any videos yet.</Text>
                <GradientButton onClick={() => navigate('/submit')}>Submit your first video</GradientButton>
              </Stack>
            </GlassCard>
          )}

          {!isLoading && !isError && jobs && jobs.length > 0 && (
            <AnimatedList>
              {jobs.map((job) => (
                <JobStatusCard key={job.id} job={job} />
              ))}
            </AnimatedList>
          )}
        </Stack>
      </Container>
    </PageWrapper>
  );
}
