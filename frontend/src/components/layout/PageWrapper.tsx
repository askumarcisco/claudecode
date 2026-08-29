import { motion } from 'framer-motion';
import { ReactNode } from 'react';

// Plain motion.div (not chakra(motion.div)) here: Chakra's own `transition`
// style prop (CSS transition tokens) collides with framer-motion's
// `transition` prop (animation timing config) when merged via chakra().
export function PageWrapper({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      style={{ minHeight: '100vh' }}
    >
      {children}
    </motion.div>
  );
}
