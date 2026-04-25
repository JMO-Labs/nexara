/**
 * @file tests/unit/session-store.test.ts
 * @brief Session store transitions: setUser flips to authenticated; reset
 *        flips to unauthenticated and clears the user.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useSession } from '@/stores/session';

const SAMPLE = {
  id: 'u1',
  email: 'a@b.com',
  username: 'alice',
  display_name: 'Alice',
  avatar_url: null,
  role: 'member',
  is_active: true,
};

describe('useSession', () => {
  beforeEach(() => useSession.getState().reset());

  it('starts unauthenticated after reset', () => {
    expect(useSession.getState().user).toBeNull();
    expect(useSession.getState().status).toBe('unauthenticated');
  });

  it('setUser(user) marks status authenticated', () => {
    useSession.getState().setUser(SAMPLE);
    expect(useSession.getState().status).toBe('authenticated');
    expect(useSession.getState().user?.username).toBe('alice');
  });

  it('setUser(null) marks status unauthenticated', () => {
    useSession.getState().setUser(SAMPLE);
    useSession.getState().setUser(null);
    expect(useSession.getState().status).toBe('unauthenticated');
    expect(useSession.getState().user).toBeNull();
  });
});
