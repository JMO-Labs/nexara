'use client';
/**
 * @file components/feed/PostBody.tsx
 * @brief Renders post text content as sanitized GFM markdown.
 */
import * as React from 'react';
import { Markdown } from '@/components/ui/Markdown';

export interface PostBodyProps {
  content: string;
  truncate?: boolean;
}

export function PostBody({ content, truncate }: PostBodyProps) {
  return <Markdown content={content} truncate={truncate} clampLines={6} />;
}

export default PostBody;
