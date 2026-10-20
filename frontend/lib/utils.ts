/**
 * @file lib/utils.ts
 * @brief Shared helpers; `cn` merges Tailwind class names.
 */
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * @brief Merge class values, deduping conflicting Tailwind utilities.
 * @param inputs class values
 * @return merged class string
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
