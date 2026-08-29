import { chakra, type BoxProps } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { ReactNode } from 'react';

const MotionBox = chakra(motion.div);

interface GlassCardProps extends Omit<BoxProps, 'children'> {
  children: ReactNode;
}

export function GlassCard({ children, ...props }: GlassCardProps) {
  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -5 }}
      p={6}
      borderRadius="2xl"
      bg="whiteAlpha.700"
      backdropFilter="blur(16px)"
      border="1px solid"
      borderColor="whiteAlpha.400"
      boxShadow="xl"
      {...props}
    >
      {children}
    </MotionBox>
  );
}
