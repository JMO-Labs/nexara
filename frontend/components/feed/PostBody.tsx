'use client';
/**
 * @file components/feed/PostBody.tsx
 * @brief Renders post text content (markdown-light: links + line breaks).
 */
import * as React from 'react';
import Typography from '@mui/joy/Typography';

const URL_RE = /(https?:\/\/[^\s<]+)/g;

export interface PostBodyProps {
  content: string;
  truncate?: boolean;
}

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  text.replace(URL_RE, (match, _url, offset: number) => {
    if (offset > lastIndex) parts.push(text.slice(lastIndex, offset));
    parts.push(
      <a
        key={`${offset}-${match}`}
        href={match}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: 'var(--joy-palette-primary-plainColor)' }}
      >
        {match}
      </a>,
    );
    lastIndex = offset + match.length;
    return match;
  });
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}

export function PostBody({ content, truncate }: PostBodyProps) {
  if (!content.trim()) return null;
  const lines = content.split('\n');
  return (
    <Typography
      level="body-md"
      sx={{
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        ...(truncate && {
          display: '-webkit-box',
          WebkitLineClamp: 6,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }),
      }}
    >
      {lines.map((line, i) => (
        <React.Fragment key={i}>
          {renderInline(line)}
          {i < lines.length - 1 ? <br /> : null}
        </React.Fragment>
      ))}
    </Typography>
  );
}

export default PostBody;
