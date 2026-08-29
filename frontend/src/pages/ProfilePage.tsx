import { useState, FormEvent } from 'react';
import {
  Alert,
  AlertIcon,
  Center,
  Heading,
  Stack,
  Text,
} from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { GlassCard } from '../components/ui/GlassCard';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import { useAuth } from '../hooks/useAuth';
import * as authService from '../services/authService';

export default function ProfilePage(): JSX.Element {
  const { user } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setSuccessMessage(null);
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await authService.updateMe({ full_name: fullName || null });
      setSuccessMessage('Profile updated successfully.');
    } catch {
      setErrorMessage('Could not update your profile. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper>
      <Center minH="100vh" px={4}>
        <GlassCard maxW="md" w="full">
          <Stack spacing={6}>
            <Heading size="lg">Your Profile</Heading>

            <Stack spacing={1}>
              <Text fontSize="sm" color="gray.500">
                Email
              </Text>
              <Text fontWeight="medium">{user?.email}</Text>
            </Stack>

            <form onSubmit={handleSubmit} noValidate>
              <Stack spacing={4}>
                {successMessage && (
                  <Alert status="success" borderRadius="lg">
                    <AlertIcon />
                    {successMessage}
                  </Alert>
                )}
                {errorMessage && (
                  <Alert status="error" borderRadius="lg">
                    <AlertIcon />
                    {errorMessage}
                  </Alert>
                )}

                <AnimatedInput
                  label="Full name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your full name"
                />

                <GradientButton type="submit" disabled={isSubmitting} opacity={isSubmitting ? 0.7 : 1} w="full">
                  {isSubmitting ? 'Saving...' : 'Save changes'}
                </GradientButton>
              </Stack>
            </form>
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}
