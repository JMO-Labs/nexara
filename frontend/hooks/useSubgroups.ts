'use client';
/**
 * @file hooks/useSubgroups.ts
 * @brief TanStack Query hooks for subgroup CRUD + membership.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMutationWithToast } from './useMutationWithToast';
import { qk } from '@/lib/query-keys';
import {
  listSubgroups,
  getSubgroup,
  createSubgroup,
  updateSubgroup,
  deleteSubgroup,
  joinSubgroup,
  leaveSubgroup,
  listMembers,
  addMember,
  changeMemberRole,
  removeMember,
  type CreateSubgroupBody,
  type UpdateSubgroupBody,
} from '@/lib/api/subgroups';

export function useSubgroupList() {
  return useQuery({
    queryKey: qk.subgroups.list(),
    queryFn: listSubgroups,
    staleTime: 60_000,
  });
}

export function useSubgroupDetail(slug: string | null | undefined) {
  return useQuery({
    queryKey: qk.subgroups.detail(slug ?? ''),
    queryFn: () => getSubgroup(slug as string),
    enabled: !!slug,
    staleTime: 30_000,
  });
}

export function useSubgroupMembers(slug: string | null | undefined) {
  return useQuery({
    queryKey: qk.subgroups.members(slug ?? ''),
    queryFn: () => listMembers(slug as string),
    enabled: !!slug,
    staleTime: 30_000,
  });
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>, slug?: string) {
  qc.invalidateQueries({ queryKey: qk.subgroups.list() });
  if (slug) {
    qc.invalidateQueries({ queryKey: qk.subgroups.detail(slug) });
    qc.invalidateQueries({ queryKey: qk.subgroups.members(slug) });
  }
}

export function useCreateSubgroup() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: CreateSubgroupBody) => createSubgroup(body),
    successKey: 'toasts.subgroups.created',
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateSubgroup(slug: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: UpdateSubgroupBody) => updateSubgroup(slug, body),
    onSuccess: () => invalidateAll(qc, slug),
  });
}

export function useDeleteSubgroup() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (slug: string) => deleteSubgroup(slug),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useJoinSubgroup() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (slug: string) => joinSubgroup(slug),
    successKey: 'toasts.subgroups.joined',
    onSuccess: (_d, slug) => invalidateAll(qc, slug),
  });
}

export function useLeaveSubgroup() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (slug: string) => leaveSubgroup(slug),
    successKey: 'toasts.subgroups.left',
    onSuccess: (_d, slug) => invalidateAll(qc, slug),
  });
}

export function useAddMember(slug: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (args: { user_id: string; role?: string }) =>
      addMember(slug, args.user_id, args.role),
    successKey: 'toasts.subgroups.member.added',
    onSuccess: () => invalidateAll(qc, slug),
  });
}

export function useChangeRole(slug: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (args: { user_id: string; role: string }) =>
      changeMemberRole(slug, args.user_id, args.role),
    onSuccess: () => invalidateAll(qc, slug),
  });
}

export function useRemoveMember(slug: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (user_id: string) => removeMember(slug, user_id),
    successKey: 'toasts.subgroups.member.removed',
    onSuccess: () => invalidateAll(qc, slug),
  });
}
