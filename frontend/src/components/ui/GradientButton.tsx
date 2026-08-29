import { chakra } from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionButton = chakra(motion.button);

type GradientButtonProps = React.ComponentProps<typeof MotionButton>;

export function GradientButton({ children, ...props }: GradientButtonProps) {
  return (
    <MotionButton
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      px={6}
      py={3}
      borderRadius="full"
      fontWeight="semibold"
      color="white"
      bgGradient="linear(to-r, brand.500, accent.500)"
      _hover={{ boxShadow: 'lg' }}
      {...props}
    >
      {children}
    </MotionButton>
  );
}
