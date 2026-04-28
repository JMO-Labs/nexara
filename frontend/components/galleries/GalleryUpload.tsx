'use client';
/**
 * @file components/galleries/GalleryUpload.tsx
 * @brief Drag-drop bulk uploader. 240px min-height, dashed border, progress queue.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import LinearProgress from '@mui/joy/LinearProgress';
import Button from '@mui/joy/Button';
import IconButton from '@mui/joy/IconButton';
import { keyframes } from '@emotion/react';
import {
  PhotoIcon,
  CheckIcon,
  XMarkIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/solid';
import { useGalleryUpload } from '@/hooks/useGalleryUpload';

const pulseAnimation = keyframes`
  0% { opacity: 0.04; }
  50% { opacity: 0.12; }
  100% { opacity: 0.04; }
`;

export interface GalleryUploadProps {
  galleryId: string;
}

export function GalleryUpload({ galleryId }: GalleryUploadProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const { jobs, enqueue, retry } = useGalleryUpload(galleryId);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    void enqueue(Array.from(e.dataTransfer.files));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) void enqueue(Array.from(e.target.files));
    e.target.value = '';
  };

  return (
    <Stack spacing={2}>
      <Box
        data-testid="upload-dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload photos — drop files or click"
        sx={{
          minHeight: '240px',
          p: 4,
          borderRadius: 'lg',
          border: dragOver ? '2px solid' : '1.5px dashed',
          borderColor: dragOver ? 'var(--joy-palette-primary-500)' : 'var(--joy-palette-neutral-outlinedBorder)',
          background: dragOver
            ? `linear-gradient(rgba(var(--joy-palette-primary-200)/0.04), rgba(var(--joy-palette-primary-200)/0.04))`
            : 'background.level1',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 200ms ease-out',
          transform: dragOver ? 'scale(1.01)' : 'scale(1)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          animation: dragOver ? `${pulseAnimation} 1.5s ease-in-out infinite` : undefined,
        }}
      >
        <PhotoIcon style={{ width: '40px', height: '40px', marginBottom: '1rem', opacity: 0.7 }} />
        <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
          Drop photos to upload
        </Typography>
        <Typography level="body-sm" sx={{ color: 'text.tertiary', mt: 1 }}>
          or click to browse
        </Typography>
        <Button sx={{ mt: 2 }} size="sm" variant="outlined" type="button">
          Choose files
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept="image/*,video/*"
          onChange={handleInputChange}
        />
      </Box>

      {jobs.length > 0 && (
        <Stack spacing={1.5} sx={{ mt: 2 }}>
          {jobs.map((job) => (
            <Stack key={job.id} data-testid="upload-row" spacing={0.75}>
              <Stack direction="row" spacing={1} alignItems="flex-start">
                {/* Thumbnail placeholder */}
                <Box
                  sx={{
                    width: '48px',
                    height: '48px',
                    borderRadius: 'sm',
                    background: 'background.level2',
                    flexShrink: 0,
                  }}
                />

                {/* Filename + status */}
                <Stack spacing={0.5} sx={{ flex: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
                    <Typography
                      data-testid="upload-filename"
                      level="body-sm"
                      noWrap
                      sx={{ flex: 1 }}
                    >
                      {job.file.name}
                    </Typography>

                    {/* Status icon / text */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                      {job.status === 'uploading' && (
                        <ArrowPathIcon style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }} />
                      )}
                      {job.status === 'done' && (
                        <CheckIcon style={{ width: '16px', height: '16px', color: 'var(--joy-palette-success-500)' }} />
                      )}
                      {job.status === 'error' && (
                        <XMarkIcon style={{ width: '16px', height: '16px', color: 'var(--joy-palette-danger-500)' }} />
                      )}
                      <Typography
                        level="body-xs"
                        sx={{
                          color:
                            job.status === 'error'
                              ? 'danger.500'
                              : job.status === 'done'
                                ? 'success.500'
                                : 'text.tertiary',
                        }}
                      >
                        {job.status === 'error'
                          ? job.error || 'Error'
                          : job.status === 'done'
                            ? 'Done'
                            : `${Math.round(job.progress)}%`}
                      </Typography>
                    </Box>
                  </Stack>

                  {/* Progress bar */}
                  <LinearProgress
                    determinate
                    value={job.progress}
                    color={job.status === 'error' ? 'danger' : job.status === 'done' ? 'success' : 'primary'}
                    sx={{
                      height: '1px',
                      '& .MuiLinearProgress-bar': {
                        backgroundImage:
                          job.status === 'uploading'
                            ? 'linear-gradient(90deg, var(--joy-palette-primary-500) 25%, transparent 25%, transparent 50%, var(--joy-palette-primary-500) 50%, var(--joy-palette-primary-500) 75%, transparent 75%, transparent)'
                            : undefined,
                        backgroundSize: job.status === 'uploading' ? '20px 1px' : undefined,
                        animation: job.status === 'uploading' ? 'slide 2s linear infinite' : undefined,
                      },
                    }}
                  />
                </Stack>

                {/* Retry button */}
                {job.status === 'error' && (
                  <IconButton
                    data-testid="retry-button"
                    size="sm"
                    variant="plain"
                    onClick={() => retry(job.id)}
                    sx={{ flexShrink: 0 }}
                  >
                    <ArrowPathIcon style={{ width: '16px', height: '16px' }} />
                  </IconButton>
                )}
              </Stack>
            </Stack>
          ))}
        </Stack>
      )}

      {/* CSS animation for stripe */}
      <style>{`
        @keyframes slide {
          0% { background-position: 0 0; }
          100% { background-position: 20px 0; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Stack>
  );
}

export default GalleryUpload;
