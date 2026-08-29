import { clsx, type ClassValue } from 'clsx';

/**
 * Combine class names conditionally.
 * Thin wrapper around clsx so components can compose Tailwind/utility
 * class strings the same way across the app.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
