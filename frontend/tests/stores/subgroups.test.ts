/**
 * @file tests/stores/subgroups.test.ts
 * @brief TDD tests for the subgroups Pinia store.
 *
 * Covers directory fetch, detail load, CRUD (create/update/archive),
 * membership actions (join/leave/role/remove), and pinned-post helpers.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useSubgroupsStore } from "~/stores/subgroups";
import type {
  JoinSubgroupResponse,
  Membership,
  Subgroup,
  SubgroupDetail,
} from "~/types/api";

const mockSubgroup: Subgroup = {
  id: "sg-1",
  name: "Photographers",
  slug: "photographers",
  description: "A place for shutterbugs",
  avatar_url: null,
  is_private: false,
  join_policy: "open",
  created_by: "user-1",
  archived_at: null,
  created_at: "2026-04-01T10:00:00Z",
  updated_at: "2026-04-01T10:00:00Z",
};

const mockDetail: SubgroupDetail = {
  ...mockSubgroup,
  member_count: 5,
  my_role: null,
  chat_channel_id: "chan-sg-1",
  pinned_post_id: null,
};

const mockMembership: Membership = {
  subgroup_id: "sg-1",
  user_id: "user-2",
  role: "member",
  invited_by: null,
  joined_at: "2026-04-02T10:00:00Z",
  username: "bob",
  display_name: "Bob",
  avatar_url: null,
};

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDel = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPost,
    put: mockPut,
    del: mockDel,
  }),
}));

describe("subgroups store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("starts with empty state", () => {
    const store = useSubgroupsStore();

    expect(store.list).toEqual([]);
    expect(store.current).toBeNull();
    expect(store.members).toEqual([]);
    expect(store.loading).toBe(false);
  });

  it("fetchList() populates the directory", async () => {
    const store = useSubgroupsStore();
    mockGet.mockResolvedValueOnce([mockSubgroup]);

    await store.fetchList();

    expect(mockGet).toHaveBeenCalledWith("/subgroups");
    expect(store.list).toHaveLength(1);
    expect(store.list[0].slug).toBe("photographers");
    expect(store.loading).toBe(false);
  });

  it("fetchDetail() loads a single subgroup and sets current", async () => {
    const store = useSubgroupsStore();
    mockGet.mockResolvedValueOnce(mockDetail);

    const result = await store.fetchDetail("photographers");

    expect(mockGet).toHaveBeenCalledWith("/subgroups/photographers");
    expect(store.current?.id).toBe("sg-1");
    expect(result.member_count).toBe(5);
  });

  it("createSubgroup() POSTs and prepends summary into list", async () => {
    const store = useSubgroupsStore();
    mockPost.mockResolvedValueOnce(mockDetail);

    const created = await store.createSubgroup({
      name: "Photographers",
      slug: "photographers",
      join_policy: "open",
    });

    expect(mockPost).toHaveBeenCalledWith("/subgroups", {
      name: "Photographers",
      slug: "photographers",
      join_policy: "open",
    });
    expect(created.id).toBe("sg-1");
    expect(store.list[0].slug).toBe("photographers");
    expect(store.current?.id).toBe("sg-1");
  });

  it("updateSubgroup() PUTs and updates list + current", async () => {
    const store = useSubgroupsStore();
    store.list = [mockSubgroup];
    store.current = mockDetail;
    const updated: SubgroupDetail = { ...mockDetail, name: "Photo Pros" };
    mockPut.mockResolvedValueOnce(updated);

    await store.updateSubgroup("photographers", { name: "Photo Pros" });

    expect(mockPut).toHaveBeenCalledWith("/subgroups/photographers", {
      name: "Photo Pros",
    });
    expect(store.list[0].name).toBe("Photo Pros");
    expect(store.current?.name).toBe("Photo Pros");
  });

  it("archiveSubgroup() DELETEs and removes from list + clears current", async () => {
    const store = useSubgroupsStore();
    store.list = [mockSubgroup];
    store.current = mockDetail;
    mockDel.mockResolvedValueOnce(undefined);

    await store.archiveSubgroup("photographers");

    expect(mockDel).toHaveBeenCalledWith("/subgroups/photographers");
    expect(store.list).toHaveLength(0);
    expect(store.current).toBeNull();
  });

  it("joinSubgroup() updates my_role + member_count when status=joined", async () => {
    const store = useSubgroupsStore();
    store.current = mockDetail;
    const response: JoinSubgroupResponse = {
      status: "joined",
      role: "member",
    };
    mockPost.mockResolvedValueOnce(response);

    const result = await store.joinSubgroup("photographers");

    expect(mockPost).toHaveBeenCalledWith("/subgroups/photographers/join");
    expect(result.status).toBe("joined");
    expect(store.current?.my_role).toBe("member");
    expect(store.current?.member_count).toBe(6);
  });

  it("joinSubgroup() leaves current untouched when status=pending", async () => {
    const store = useSubgroupsStore();
    store.current = mockDetail;
    mockPost.mockResolvedValueOnce({
      status: "pending",
      policy: "admin_approval",
    });

    const result = await store.joinSubgroup("photographers");

    expect(result.status).toBe("pending");
    expect(store.current?.my_role).toBeNull();
    expect(store.current?.member_count).toBe(5);
  });

  it("leaveSubgroup() resets my_role and decrements member_count", async () => {
    const store = useSubgroupsStore();
    store.current = { ...mockDetail, my_role: "member" };
    mockPost.mockResolvedValueOnce(undefined);

    await store.leaveSubgroup("photographers");

    expect(mockPost).toHaveBeenCalledWith("/subgroups/photographers/leave");
    expect(store.current?.my_role).toBeNull();
    expect(store.current?.member_count).toBe(4);
  });

  it("fetchMembers() populates members", async () => {
    const store = useSubgroupsStore();
    mockGet.mockResolvedValueOnce([mockMembership]);

    await store.fetchMembers("photographers");

    expect(mockGet).toHaveBeenCalledWith("/subgroups/photographers/members");
    expect(store.members).toHaveLength(1);
    expect(store.members[0].user_id).toBe("user-2");
  });

  it("changeMemberRole() updates the matching membership in place", async () => {
    const store = useSubgroupsStore();
    store.members = [mockMembership];
    const promoted: Membership = { ...mockMembership, role: "moderator" };
    mockPost.mockResolvedValueOnce(promoted);

    await store.changeMemberRole("photographers", "user-2", "moderator");

    expect(mockPost).toHaveBeenCalledWith(
      "/subgroups/photographers/members/user-2/role",
      { role: "moderator" },
    );
    expect(store.members[0].role).toBe("moderator");
  });

  it("removeMember() drops the row and decrements member_count on current", async () => {
    const store = useSubgroupsStore();
    store.members = [mockMembership];
    store.current = mockDetail;
    mockDel.mockResolvedValueOnce(undefined);

    await store.removeMember("photographers", "user-2");

    expect(mockDel).toHaveBeenCalledWith(
      "/subgroups/photographers/members/user-2",
    );
    expect(store.members).toHaveLength(0);
    expect(store.current?.member_count).toBe(4);
  });

  it("pinPost() POSTs and updates current.pinned_post_id", async () => {
    const store = useSubgroupsStore();
    store.current = mockDetail;
    mockPost.mockResolvedValueOnce({
      post_id: "post-9",
      subgroup_id: "sg-1",
    });

    await store.pinPost("photographers", "post-9");

    expect(mockPost).toHaveBeenCalledWith(
      "/subgroups/photographers/pinned-post",
      { post_id: "post-9" },
    );
    expect(store.current?.pinned_post_id).toBe("post-9");
  });

  it("unpinPost() DELETEs and clears current.pinned_post_id", async () => {
    const store = useSubgroupsStore();
    store.current = { ...mockDetail, pinned_post_id: "post-9" };
    mockDel.mockResolvedValueOnce(undefined);

    await store.unpinPost("photographers");

    expect(mockDel).toHaveBeenCalledWith(
      "/subgroups/photographers/pinned-post",
    );
    expect(store.current?.pinned_post_id).toBeNull();
  });
});
