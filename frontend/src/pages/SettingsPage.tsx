import { useState, FormEvent } from 'react';
import { Alert, AlertIcon, Divider, Heading, Stack, Text } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { AnimatedInput } from '../components/ui/AnimatedInput';
import { GradientButton } from '../components/ui/GradientButton';
import * as settingsService from '../services/settingsService';

export default function SettingsPage(): JSX.Element {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setValidationError(null);
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setValidationError('Please fill in all password fields.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setValidationError('New password and confirmation do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      // TODO: backend endpoint not yet implemented — wire up when available.
      await settingsService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccessMessage('Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setErrorMessage('Password change is not available yet. Please try again later.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper>
      <MeshBackground />
      <Stack spacing={8} maxW="2xl" mx="auto" px={4} py={12}>
        <Heading size="lg">Settings</Heading>

        <GlassCard>
          <Stack spacing={6}>
            <Stack spacing={3}>
              <Heading size="md">Change password</Heading>
              <Alert status="info" borderRadius="lg">
                <AlertIcon />
                Password change is coming soon.
              </Alert>

              <form onSubmit={handleSubmit} noValidate>
                <Stack spacing={4}>
                  {validationError && (
                    <Alert status="error" borderRadius="lg">
                      <AlertIcon />
                      {validationError}
                    </Alert>
                  )}
                  {errorMessage && (
                    <Alert status="error" borderRadius="lg">
                      <AlertIcon />
                      {errorMessage}
                    </Alert>
                  )}
                  {successMessage && (
                    <Alert status="success" borderRadius="lg">
                      <AlertIcon />
                      {successMessage}
                    </Alert>
                  )}

                  <AnimatedInput
                    label="Current password"
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter your current password"
                    autoComplete="current-password"
                  />
                  <AnimatedInput
                    label="New password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Enter a new password"
                    autoComplete="new-password"
                  />
                  <AnimatedInput
                    label="Confirm new password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                    autoComplete="new-password"
                  />

                  <GradientButton type="submit" disabled={isSubmitting} opacity={isSubmitting ? 0.7 : 1} w="full">
                    {isSubmitting ? 'Saving...' : 'Change password'}
                  </GradientButton>
                </Stack>
              </form>
            </Stack>

            <Divider />

            <Stack spacing={2}>
              <Heading size="md">Output folder</Heading>
              <Text color="gray.600" fontSize="sm">
                Summary videos are saved to the server&apos;s configured output folder
                (set by the <code>OUTPUT_DIR</code> environment variable) and are not
                user-configurable per request in this MVP. Once a job finishes, download
                the rendered video from that job&apos;s detail page.
              </Text>
            </Stack>
          </Stack>
        </GlassCard>
      </Stack>
    </PageWrapper>
  );
}
