/**
 * @file stores/subgroups.ts
 * @brief Pinia store for subgroup directory, detail, and membership.
 *
 * Manages the list of subgroups, the currently viewed subgroup's detail
 * payload, and the member list for that subgroup. Exposes CRUD helpers
 * (fetch/create/update/archive), membership actions (join/leave/role/remove),
 * and pinned-post helpers (pin/unpin). All HTTP calls go through useApi().
 */

import { ref } from "vue";
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import type {
  JoinSubgroupResponse,
  Membership,
  Subgroup,
  SubgroupCreatePayload,
  SubgroupDetail,
  SubgroupRole,
  SubgroupUpdatePayload,
} from "~/types/api";

export const useSubgroupsStore = defineStore("subgroups", () => {
  /** @brief Directory list of subgroups visible to the current user. */
  const list = ref<Subgroup[]>([]);

  /** @brief Currently viewed subgroup detail (null when none loaded). */
  const current = ref<SubgroupDetail | null>(null);

  /** @brief Members of the currently viewed subgroup. */
  const members = ref<Membership[]>([]);

  /** @brief Whether a fetch/list operation is in progress. */
  const loading = ref(false);

  /**
   * @brief Fetch the directory of subgroups visible to the current user.
   * @throws Error if the request fails.
   */
  async function fetchList(): Promise<void> {
    loading.value = true;
    try {
      const api = useApi();
      list.value = await api.get<Subgroup[]>("/subgroups");
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Fetch a single subgroup detail by slug.
   * @param slug - URL-safe subgroup slug.
   */
  async function fetchDetail(slug: string): Promise<SubgroupDetail> {
    loading.value = true;
    try {
      const api = useApi();
      const detail = await api.get<SubgroupDetail>(`/subgroups/${slug}`);
      current.value = detail;
      return detail;
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Create a new subgroup. The creator becomes owner.
   * @param payload - Create payload.
   * @returns The newly created subgroup detail.
   */
  async function createSubgroup(
    payload: SubgroupCreatePayload,
  ): Promise<SubgroupDetail> {
    const api = useApi();
    const created = await api.post<SubgroupDetail>("/subgroups", payload);
    // Prepend summary into list for immediate directory update.
    const summary: Subgroup = {
      id: created.id,
      name: created.name,
      slug: created.slug,
      description: created.description,
      avatar_url: created.avatar_url,
      is_private: created.is_private,
      join_policy: created.join_policy,
      created_by: created.created_by,
      archived_at: created.archived_at,
      created_at: created.created_at,
      updated_at: created.updated_at,
    };
    list.value = [summary, ...list.value];
    current.value = created;
    return created;
  }

  /**
   * @brief Update fields on an existing subgroup (owner/mod/admin only).
   * @param slug - Subgroup slug.
   * @param payload - Partial update.
   */
  async function updateSubgroup(
    slug: string,
    payload: SubgroupUpdatePayload,
  ): Promise<SubgroupDetail> {
    const api = useApi();
    const updated = await api.put<SubgroupDetail>(
      `/subgroups/${slug}`,
      payload,
    );
    const idx = list.value.findIndex((s) => s.slug === slug);
    if (idx !== -1) {
      list.value[idx] = { ...list.value[idx], ...updated };
    }
    if (current.value?.slug === slug) {
      current.value = updated;
    }
    return updated;
  }

  /**
   * @brief Archive (soft-delete) a subgroup.
   * @param slug - Subgroup slug.
   */
  async function archiveSubgroup(slug: string): Promise<void> {
    const api = useApi();
    await api.del(`/subgroups/${slug}`);
    list.value = list.value.filter((s) => s.slug !== slug);
    if (current.value?.slug === slug) {
      current.value = null;
    }
  }

  /**
   * @brief Join (or request to join) a subgroup per its policy.
   *
   * On an ``open`` subgroup, the response is ``{status: "joined"}``
   * and ``current.my_role`` is updated. For invite-only/approval
   * policies the response is ``{status: "pending"}``.
   *
   * @param slug - Subgroup slug.
   */
  async function joinSubgroup(slug: string): Promise<JoinSubgroupResponse> {
    const api = useApi();
    const result = await api.post<JoinSubgroupResponse>(
      `/subgroups/${slug}/join`,
    );
    if (result.status === "joined" && current.value?.slug === slug) {
      current.value = {
        ...current.value,
        my_role: result.role ?? "member",
        member_count: current.value.member_count + 1,
      };
    }
    return result;
  }

  /**
   * @brief Leave a subgroup.
   * @param slug - Subgroup slug.
   */
  async function leaveSubgroup(slug: string): Promise<void> {
    const api = useApi();
    await api.post(`/subgroups/${slug}/leave`);
    if (current.value?.slug === slug) {
      current.value = {
        ...current.value,
        my_role: null,
        member_count: Math.max(0, current.value.member_count - 1),
      };
    }
  }

  /**
   * @brief Fetch the full member list for a subgroup.
   * @param slug - Subgroup slug.
   */
  async function fetchMembers(slug: string): Promise<void> {
    const api = useApi();
    members.value = await api.get<Membership[]>(`/subgroups/${slug}/members`);
  }

  /**
   * @brief Change a member's role (owner or admin only).
   * @param slug - Subgroup slug.
   * @param userId - Target user ID.
   * @param role - New role.
   */
  async function changeMemberRole(
    slug: string,
    userId: string,
    role: SubgroupRole,
  ): Promise<Membership> {
    const api = useApi();
    const updated = await api.post<Membership>(
      `/subgroups/${slug}/members/${userId}/role`,
      { role },
    );
    const idx = members.value.findIndex((m) => m.user_id === userId);
    if (idx !== -1) {
      members.value[idx] = { ...members.value[idx], ...updated };
    }
    return updated;
  }

  /**
   * @brief Remove a member (owner/moderator/admin only).
   * @param slug - Subgroup slug.
   * @param userId - Target user ID.
   */
  async function removeMember(slug: string, userId: string): Promise<void> {
    const api = useApi();
    await api.del(`/subgroups/${slug}/members/${userId}`);
    members.value = members.value.filter((m) => m.user_id !== userId);
    if (current.value?.slug === slug) {
      current.value = {
        ...current.value,
        member_count: Math.max(0, current.value.member_count - 1),
      };
    }
  }

  /**
   * @brief Pin a post as the subgroup announcement.
   * @param slug - Subgroup slug.
   * @param postId - Post ID to pin.
   */
  async function pinPost(slug: string, postId: string): Promise<void> {
    const api = useApi();
    await api.post<{ post_id: string; subgroup_id: string }>(
      `/subgroups/${slug}/pinned-post`,
      { post_id: postId },
    );
    if (current.value?.slug === slug) {
      current.value = { ...current.value, pinned_post_id: postId };
    }
  }

  /**
   * @brief Remove the pinned post for a subgroup.
   * @param slug - Subgroup slug.
   */
  async function unpinPost(slug: string): Promise<void> {
    const api = useApi();
    await api.del(`/subgroups/${slug}/pinned-post`);
    if (current.value?.slug === slug) {
      current.value = { ...current.value, pinned_post_id: null };
    }
  }

  return {
    list,
    current,
    members,
    loading,
    fetchList,
    fetchDetail,
    createSubgroup,
    updateSubgroup,
    archiveSubgroup,
    joinSubgroup,
    leaveSubgroup,
    fetchMembers,
    changeMemberRole,
    removeMember,
    pinPost,
    unpinPost,
  };
});
