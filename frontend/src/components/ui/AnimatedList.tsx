import { chakra } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { ReactNode } from 'react';

const MotionBox = chakra(motion.div);

export function AnimatedList({ children }: { children: ReactNode[] }) {
  return (
    <MotionBox initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      {children.map((child, i) => (
        <MotionBox key={i} variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
          {child}
        </MotionBox>
      ))}
    </MotionBox>
  );
}
