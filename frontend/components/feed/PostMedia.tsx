'use client';
/**
 * @file components/feed/PostMedia.tsx
 * @brief Media grid for post attachments. 1/2/3+ layouts. Images only for now.
 */
import Box from '@mui/joy/Box';
import type { PostMedia as Media } from '@/lib/api/posts';

export interface PostMediaProps {
  media: Media[];
  onClick?: (index: number) => void;
}

function isImage(m: Media) {
  return m.mime_type.startsWith('image/');
}

export function PostMedia({ media, onClick }: PostMediaProps) {
  if (!media || media.length === 0) return null;
  const visible = media.slice(0, 4);
  const overflow = Math.max(0, media.length - 4);

  return (
    <Box
      sx={{
        display: 'grid',
        gap: 1,
        borderRadius: 'md',
        overflow: 'hidden',
        gridTemplateColumns:
          visible.length === 1 ? '1fr' : visible.length === 2 ? '1fr 1fr' : '1fr 1fr',
        gridTemplateRows: visible.length > 2 ? 'repeat(2, 1fr)' : '1fr',
      }}
    >
      {visible.map((m, i) => (
        <Box
          key={m.id}
          onClick={() => onClick?.(i)}
          sx={{
            position: 'relative',
            cursor: onClick ? 'pointer' : 'default',
            aspectRatio: visible.length === 1 ? '16 / 10' : '1 / 1',
            overflow: 'hidden',
            backgroundColor: 'background.level1',
          }}
        >
          {isImage(m) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={m.thumbnail_url ?? m.url}
              alt=""
              loading="lazy"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <video
              src={m.url}
              controls
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          )}
          {i === 3 && overflow > 0 ? (
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'common.white',
                fontFamily: 'display',
                fontSize: 24,
                background: 'rgba(0,0,0,0.5)',
              }}
            >
              +{overflow}
            </Box>
          ) : null}
        </Box>
      ))}
    </Box>
  );
}

export default PostMedia;
