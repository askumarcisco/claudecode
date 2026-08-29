import { Center, Heading, Stack } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { LoginForm } from '../components/auth/LoginForm';

export default function LoginPage(): JSX.Element {
  return (
    <PageWrapper>
      <MeshBackground />
      <Center minH="100vh" px={4}>
        <GlassCard maxW="md" w="full">
          <Stack spacing={6}>
            <Heading size="lg" textAlign="center" bgGradient="linear(to-r, brand.500, accent.500)" bgClip="text">
              Welcome back
            </Heading>
            <LoginForm />
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}
