import { Center, Heading, Stack, Tab, TabList, TabPanel, TabPanels, Tabs } from '@chakra-ui/react';
import { PageWrapper } from '../components/layout/PageWrapper';
import { MeshBackground } from '../components/layout/MeshBackground';
import { GlassCard } from '../components/ui/GlassCard';
import { UrlSubmitForm } from '../components/jobs/UrlSubmitForm';
import { FileUploadForm } from '../components/jobs/FileUploadForm';

export default function SubmitPage(): JSX.Element {
  return (
    <PageWrapper>
      <MeshBackground />
      <Center minH="100vh" px={4}>
        <GlassCard maxW="lg" w="full">
          <Stack spacing={6}>
            <Heading size="lg" textAlign="center" bgGradient="linear(to-r, brand.500, accent.500)" bgClip="text">
              Submit a video
            </Heading>

            <Tabs isFitted colorScheme="purple">
              <TabList>
                <Tab>YouTube URL</Tab>
                <Tab>Upload file</Tab>
              </TabList>
              <TabPanels>
                <TabPanel px={0}>
                  <UrlSubmitForm />
                </TabPanel>
                <TabPanel px={0}>
                  <FileUploadForm />
                </TabPanel>
              </TabPanels>
            </Tabs>
          </Stack>
        </GlassCard>
      </Center>
    </PageWrapper>
  );
}
