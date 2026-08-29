import { chakra, FormControl, FormLabel, FormErrorMessage } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { InputHTMLAttributes, forwardRef, useId } from 'react';

const MotionInput = chakra(motion.input);

// Omit the native drag/animation event handlers: their DOM event types
// collide with framer-motion's own onDrag*/onAnimation* prop types once
// spread onto MotionInput (chakra(motion.input)).
type NativeInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd' | 'onAnimationIteration'
>;

interface Props extends NativeInputProps {
  label?: string;
  error?: string;
}

export const AnimatedInput = forwardRef<HTMLInputElement, Props>(({ label, error, id, ...props }, ref) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;

  return (
    <FormControl isInvalid={!!error}>
      {label && (
        <FormLabel htmlFor={inputId} fontSize="sm" fontWeight="medium">
          {label}
        </FormLabel>
      )}
      <MotionInput
        id={inputId}
        ref={ref}
        whileFocus={{ scale: 1.01 }}
        w="full"
        px={4}
        py={3}
        borderRadius="xl"
        border="2px solid"
        borderColor={error ? 'red.500' : 'gray.200'}
        _focus={{ borderColor: 'brand.500', outline: 'none' }}
        {...props}
      />
      {error && <FormErrorMessage>{error}</FormErrorMessage>}
    </FormControl>
  );
});

AnimatedInput.displayName = 'AnimatedInput';
