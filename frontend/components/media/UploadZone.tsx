'use client';
/**
 * @file components/media/UploadZone.tsx
 * @brief Drag-and-drop + click-to-pick upload zone. Sequential uploads with
 *        per-file progress.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import LinearProgress from '@mui/joy/LinearProgress';
import { Button } from '@/components/ui';
import { uploadFile, type MediaItem } from '@/lib/api/media';

export interface UploadZoneProps {
  onComplete?: (media: MediaItem) => void;
}

interface Job {
  file: File;
  progress: number;
  done: boolean;
  error: string | null;
}

export function UploadZone({ onComplete }: UploadZoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [dragOver, setDragOver] = React.useState(false);

  const start = React.useCallback(
    async (files: File[]) => {
      const initial: Job[] = files.map((f) => ({ file: f, progress: 0, done: false, error: null }));
      setJobs((j) => [...j, ...initial]);
      const offset = jobs.length;
      for (let i = 0; i < files.length; i++) {
        const idx = offset + i;
        try {
          const m = await uploadFile(files[i], (pct) =>
            setJobs((js) => js.map((j, ji) => (ji === idx ? { ...j, progress: pct } : j))),
          );
          setJobs((js) =>
            js.map((j, ji) => (ji === idx ? { ...j, done: true, progress: 100 } : j)),
          );
          onComplete?.(m);
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          setJobs((js) => js.map((j, ji) => (ji === idx ? { ...j, error: msg } : j)));
        }
      }
    },
    [jobs.length, onComplete],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    void start(Array.from(e.dataTransfer.files));
  };

  return (
    <Stack spacing={2}>
      <Box
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload media — drop files or click"
        sx={{
          p: 4,
          borderRadius: 'lg',
          border: '2px dashed',
          borderColor: dragOver ? 'primary.outlinedBorder' : 'divider',
          background: dragOver ? 'primary.softBg' : 'background.level1',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'background 120ms',
        }}
      >
        <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
          Drop files here
        </Typography>
        <Typography level="body-sm" sx={{ color: 'text.tertiary' }}>
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
          onChange={(e) => {
            if (e.target.files) void start(Array.from(e.target.files));
            e.target.value = '';
          }}
        />
      </Box>
      {jobs.length > 0 && (
        <Stack spacing={1}>
          {jobs.map((j, i) => (
            <Stack key={i} spacing={0.5}>
              <Stack direction="row" justifyContent="space-between">
                <Typography level="body-sm" noWrap sx={{ flex: 1, mr: 1 }}>
                  {j.file.name}
                </Typography>
                <Typography level="body-xs" sx={{ color: j.error ? 'danger.500' : 'text.tertiary' }}>
                  {j.error ? j.error : j.done ? 'Done' : `${Math.round(j.progress)}%`}
                </Typography>
              </Stack>
              <LinearProgress
                determinate
                value={j.progress}
                color={j.error ? 'danger' : j.done ? 'success' : 'primary'}
              />
            </Stack>
          ))}
        </Stack>
      )}
    </Stack>
  );
}

export default UploadZone;
