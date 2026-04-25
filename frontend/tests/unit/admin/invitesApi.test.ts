/**
 * @file tests/unit/admin/invitesApi.test.ts
 * @brief Tests for invites API wrapper functions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '@/lib/api/client';
import { listInvites, createInvite, revokeInvite } from '@/lib/api/invites';

vi.mock('@/lib/api/client');

describe('invitesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listInvites', () => {
    it('should call apiGet with correct path', async () => {
      const mockInvites = [
        {
          id: 'invite-1',
          email: 'test@example.com',
          role: 'member',
          created_at: new Date(),
          expires_at: new Date(Date.now() + 86400000),
          used_at: null,
          code: 'abc123',
        },
      ];
      vi.mocked(client.apiGet).mockResolvedValue(mockInvites);

      const result = await listInvites();

      expect(client.apiGet).toHaveBeenCalledWith('/api/v1/invites');
      expect(result).toEqual(mockInvites);
    });
  });

  describe('createInvite', () => {
    it('should call apiPost with email and role', async () => {
      const mockResponse = {
        id: 'invite-1',
        code: 'abc123',
        email: 'test@example.com',
        role: 'member',
      };
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const result = await createInvite('test@example.com', 'member');

      expect(client.apiPost).toHaveBeenCalledWith('/api/v1/invites', {
        email: 'test@example.com',
        role: 'member',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('revokeInvite', () => {
    it('should call apiDelete with invite id', async () => {
      const mockResponse = { message: 'Invite revoked' };
      vi.mocked(client.apiDelete).mockResolvedValue(mockResponse);

      const result = await revokeInvite('invite-1');

      expect(client.apiDelete).toHaveBeenCalledWith('/api/v1/invites/invite-1');
      expect(result).toEqual(mockResponse);
    });
  });
});
