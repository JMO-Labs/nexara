/**
 * @file tests/unit/galleries/Lightbox.test.tsx
 * @brief Lightbox keyboard nav: arrows advance, Esc closes.
 */
import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { Lightbox } from '@/components/galleries/Lightbox';
import type { GalleryItem } from '@/lib/api/galleries';

const items: GalleryItem[] = [
  {
    id: 'i1',
    gallery_id: 'g1',
    media_id: 'm1',
    added_by: 'u1',
    caption: 'one',
    position: 0,
    created_at: '2026-04-25T00:00:00Z',
  },
  {
    id: 'i2',
    gallery_id: 'g1',
    media_id: 'm2',
    added_by: 'u1',
    caption: 'two',
    position: 1,
    created_at: '2026-04-25T00:00:00Z',
  },
];

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe('Lightbox', () => {
  it('Esc fires onClose', () => {
    const onClose = vi.fn();
    wrap(<Lightbox items={items} index={0} onClose={onClose} onIndexChange={() => {}} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
  it('ArrowRight advances index', () => {
    const onIdx = vi.fn();
    wrap(<Lightbox items={items} index={0} onClose={() => {}} onIndexChange={onIdx} />);
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(onIdx).toHaveBeenCalledWith(1);
  });
  it('ArrowLeft decrements index', () => {
    const onIdx = vi.fn();
    wrap(<Lightbox items={items} index={1} onClose={() => {}} onIndexChange={onIdx} />);
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(onIdx).toHaveBeenCalledWith(0);
  });
});
