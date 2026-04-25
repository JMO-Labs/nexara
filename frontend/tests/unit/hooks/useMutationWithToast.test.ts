/**
 * @file tests/unit/hooks/useMutationWithToast.test.ts
 * @brief Test useMutationWithToast wrapper for automatic toast handling.
 */
import * as React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMutationWithToast } from '@/hooks/useMutationWithToast';
import { useToasts } from '@/stores/toasts';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.success.example': 'Success!',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient();
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = 'Wrapper';
  return Wrapper;
};

describe('useMutationWithToast', () => {
  beforeEach(() => {
    useToasts.getState().clear();
    vi.clearAllMocks();
  });

  it('shows success toast with successKey', async () => {
    const mutationFn = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          successKey: 'toasts.success.example',
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const toasts = useToasts.getState().items;
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({
      variant: 'success',
      message: 'Success!',
    });
  });

  it('shows error toast with errorKey', async () => {
    const err = new Error('Test error');
    const mutationFn = vi.fn().mockRejectedValue(err);
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          errorKey: 'toasts.errors.generic',
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const toasts = useToasts.getState().items;
    expect(toasts).toHaveLength(1);
    expect(toasts[0]).toMatchObject({
      variant: 'danger',
      message: 'Something went wrong',
    });
  });

  it('respects silentSuccess flag', async () => {
    const mutationFn = vi.fn().mockResolvedValue({ ok: true });
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          successKey: 'toasts.success.example',
          silentSuccess: true,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const toasts = useToasts.getState().items;
    expect(toasts).toHaveLength(0);
  });

  it('respects silentError flag', async () => {
    const err = new Error('Test error');
    const mutationFn = vi.fn().mockRejectedValue(err);
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          silentError: true,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    const toasts = useToasts.getState().items;
    expect(toasts).toHaveLength(0);
  });

  it('calls original onSuccess callback', async () => {
    const onSuccess = vi.fn();
    const mutationFn = vi.fn().mockResolvedValue({ id: 1 });
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          successKey: 'toasts.success.example',
          onSuccess,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(onSuccess).toHaveBeenCalledWith({ id: 1 }, undefined, undefined);
  });

  it('calls original onError callback', async () => {
    const onError = vi.fn();
    const err = new Error('Test error');
    const mutationFn = vi.fn().mockRejectedValue(err);
    const { result } = renderHook(
      () =>
        useMutationWithToast({
          mutationFn,
          onError,
        }),
      { wrapper: createWrapper() },
    );

    act(() => {
      result.current.mutate(undefined);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(onError).toHaveBeenCalledWith(err, undefined, undefined);
  });
});
