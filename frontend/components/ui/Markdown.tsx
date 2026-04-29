'use client';
/**
 * @file components/ui/Markdown.tsx
 * @brief Safe GFM markdown renderer. Sanitized via rehype-sanitize.
 *        Headings flatten to body weight to fit chat/post density.
 */
import * as React from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import Box from '@mui/joy/Box';

export interface MarkdownProps {
  content: string;
  truncate?: boolean;
  /** Lines to clamp when truncate is set. Default 6. */
  clampLines?: number;
  /** Override font size. Default inherits parent. */
  size?: 'sm' | 'md';
}

const schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [...(defaultSchema.attributes?.a || []), ['target'], ['rel']],
    code: [...(defaultSchema.attributes?.code || []), ['className']],
  },
  clobberPrefix: 'nx-md-',
};

const components: Components = {
  a: ({ children, href, ...rest }) => (
    <a {...rest} href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  // Flatten headings — chat/posts already have their own heading hierarchy.
  h1: ({ children }) => <strong>{children}</strong>,
  h2: ({ children }) => <strong>{children}</strong>,
  h3: ({ children }) => <strong>{children}</strong>,
  h4: ({ children }) => <strong>{children}</strong>,
  h5: ({ children }) => <strong>{children}</strong>,
  h6: ({ children }) => <strong>{children}</strong>,
};

export function Markdown({ content, truncate, clampLines = 6, size = 'md' }: MarkdownProps) {
  if (!content?.trim()) return null;
  return (
    <Box
      className="nx-md"
      sx={{
        fontSize: size === 'sm' ? '0.875rem' : 'inherit',
        lineHeight: 1.55,
        color: 'text.primary',
        wordBreak: 'break-word',
        '& p': { m: 0, '& + p': { mt: 0.75 } },
        '& a': { color: 'var(--joy-palette-primary-plainColor)', textDecoration: 'underline' },
        '& code': {
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          fontSize: '0.9em',
          px: 0.5,
          py: 0.125,
          borderRadius: '4px',
          bgcolor: 'background.level1',
        },
        '& pre': {
          fontFamily: 'var(--font-mono, ui-monospace, monospace)',
          fontSize: '0.85em',
          p: 1.25,
          borderRadius: 'sm',
          bgcolor: 'background.level1',
          overflow: 'auto',
          m: 0,
          mt: 0.75,
          '& code': { p: 0, bgcolor: 'transparent' },
        },
        '& blockquote': {
          m: 0,
          mt: 0.75,
          pl: 1.25,
          borderLeft: '3px solid',
          borderColor: 'divider',
          color: 'text.secondary',
        },
        '& ul, & ol': { m: 0, mt: 0.5, pl: 2.5 },
        '& li + li': { mt: 0.25 },
        '& table': {
          borderCollapse: 'collapse',
          mt: 0.75,
          fontSize: '0.9em',
        },
        '& th, & td': {
          border: '1px solid',
          borderColor: 'divider',
          px: 1,
          py: 0.5,
          textAlign: 'left',
        },
        '& th': { bgcolor: 'background.level1' },
        '& hr': { border: 0, borderTop: '1px solid', borderColor: 'divider', my: 1 },
        '& img': { maxWidth: '100%', borderRadius: 'sm' },
        '& input[type="checkbox"]': { mr: 0.5 },
        ...(truncate && {
          display: '-webkit-box',
          WebkitLineClamp: clampLines,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }),
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, schema]]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
}

export default Markdown;
