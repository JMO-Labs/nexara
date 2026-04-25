/**
 * @file tests/unit/api-client.test.ts
 * @brief Phase 0 smoke: api() attaches Bearer, parses error envelope, retries
 *        once on 401 after a successful refresh.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api } from '@/lib/api/client';
import { setAccessToken } from '@/lib/auth/session';
import { ApiError } from '@/lib/api/errors';

describe('api client', () => {
  beforeEach(() => {
    setAccessToken('initial-token');
    vi.restoreAllMocks();
  });

  it('attaches Bearer header from session', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await api('/api/v1/me');
    const headers = (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer initial-token');
  });

  it('throws ApiError shaped from error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: 'forbidden', message: 'no.' } }),
          { status: 403, headers: { 'content-type': 'application/json' } },
        ),
      ),
    );

    await expect(api('/api/v1/x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 403,
      code: 'forbidden',
    });
  });

  it('retries once after a 401 if refresh succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'fresh' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    const out = await api<{ ok: boolean }>('/api/v1/me');
    expect(out).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const lastHeaders = (fetchMock.mock.calls[2][1] as RequestInit).headers as Headers;
    expect(lastHeaders.get('Authorization')).toBe('Bearer fresh');
  });

  it('gives up after 401 if refresh fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(new Response('', { status: 401 }))
        .mockResolvedValueOnce(new Response('', { status: 401 })),
    );

    await expect(api('/api/v1/me')).rejects.toBeInstanceOf(ApiError);
  });
});
