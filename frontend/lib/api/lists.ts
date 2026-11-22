/**
 * @file lib/api/lists.ts
 * @brief Lists REST client: lists, items, completion, signups and members.
 *        Wire format is snake_case; callers see camelCase (see listTypes).
 */
import { apiDelete, apiGet, apiPost, apiPut, seg } from "./client";
import {
  camelize,
  snakeize,
  type List,
  type ListActivity,
  type ListActivityPage,
  type ListCreateInput,
  type ListItem,
  type ListUser,
  type ListItemCreateInput,
  type ListItemPage,
  type ListItemSignup,
  type ListItemUpdateInput,
  type ListMember,
  type ListMemberAddInput,
  type ListPage,
  type ListUpdateInput,
  type SignupClaimInput,
} from "./listTypes";

const BASE = "/api/v1/lists";

interface Pagination {
  cursor?: string | null;
  has_more?: boolean;
}

export interface PageParams {
  cursor?: string;
  limit?: number;
  sortBy?: string;
}

const qs = (p: PageParams = {}) => {
  const q = new URLSearchParams();
  if (p.cursor) q.set("cursor", p.cursor);
  if (p.limit !== undefined) q.set("limit", String(p.limit));
  if (p.sortBy) q.set("sort_by", p.sortBy);
  const s = q.toString();
  return s ? `?${s}` : "";
};

const next = (p?: Pagination) =>
  p?.has_more && p.cursor ? p.cursor : undefined;
const one = <T>(raw: unknown) => camelize<T>(raw);
const user = (raw: unknown) => (raw ? one<ListUser>(raw) : null);

/** Camelize an item and its nested assignee. */
const item = (raw: unknown): ListItem => {
  const i = one<ListItem>(raw);
  return { ...i, assignee: user((raw as { assignee?: unknown }).assignee) };
};

/** Camelize an activity row and its nested users. */
const activity = (raw: unknown): ListActivity => {
  const a = one<ListActivity & { target_user?: unknown }>(raw);
  const r = raw as { actor?: unknown; target_user?: unknown };
  return { ...a, actor: user(r.actor), targetUser: user(r.target_user) };
};

const itemUrl = (listId: string, itemId: string, tail: string) =>
  `${BASE}/${seg(listId)}/items/${seg(itemId)}/${tail}`;

export const listApi = {
  async getLists(p?: PageParams): Promise<ListPage> {
    const r = await apiGet<{ lists: unknown[]; pagination?: Pagination }>(
      `${BASE}${qs(p)}`,
    );
    return {
      lists: r.lists.map((l) => one<List>(l)),
      nextCursor: next(r.pagination),
    };
  },
  async getList(id: string): Promise<List> {
    return one(await apiGet(`${BASE}/${seg(id)}`));
  },
  async createList(data: ListCreateInput): Promise<List> {
    return one(await apiPost(BASE, snakeize(data)));
  },
  async updateList(id: string, data: ListUpdateInput): Promise<List> {
    return one(await apiPut(`${BASE}/${seg(id)}`, snakeize(data)));
  },
  deleteList(id: string): Promise<void> {
    return apiDelete(`${BASE}/${seg(id)}`);
  },
  /** Archive via POST /lists/{id}/archive. */
  async archiveList(id: string): Promise<List> {
    return one(await apiPost(`${BASE}/${seg(id)}/archive`));
  },
  async listItems(listId: string, p?: PageParams): Promise<ListItemPage> {
    const r = await apiGet<{ items: unknown[]; pagination?: Pagination }>(
      `${BASE}/${seg(listId)}/items${qs(p)}`,
    );
    return {
      items: r.items.map(item),
      nextCursor: next(r.pagination),
    };
  },
  async createItem(
    listId: string,
    data: ListItemCreateInput,
  ): Promise<ListItem> {
    return one(await apiPost(`${BASE}/${seg(listId)}/items`, data));
  },
  async updateItem(
    listId: string,
    itemId: string,
    data: ListItemUpdateInput,
  ): Promise<ListItem> {
    return one(
      await apiPut(`${BASE}/${seg(listId)}/items/${seg(itemId)}`, data),
    );
  },
  deleteItem(listId: string, itemId: string): Promise<void> {
    return apiDelete(`${BASE}/${seg(listId)}/items/${seg(itemId)}`);
  },
  async completeItem(listId: string, itemId: string): Promise<ListItem> {
    return one(
      await apiPost(`${BASE}/${seg(listId)}/items/${seg(itemId)}/complete`),
    );
  },
  async uncompleteItem(listId: string, itemId: string): Promise<ListItem> {
    return one(
      await apiPost(`${BASE}/${seg(listId)}/items/${seg(itemId)}/uncomplete`),
    );
  },
  async claimSignup(
    listId: string,
    itemId: string,
    data: SignupClaimInput = {},
  ): Promise<ListItemSignup> {
    return one(
      await apiPost(
        `${BASE}/${seg(listId)}/items/${seg(itemId)}/signups`,
        data,
      ),
    );
  },
  releaseSignup(listId: string, itemId: string): Promise<void> {
    return apiDelete(`${BASE}/${seg(listId)}/items/${seg(itemId)}/signups`);
  },
  async takeItem(listId: string, itemId: string): Promise<ListItem> {
    return item(await apiPost(itemUrl(listId, itemId, "take")));
  },
  async assignItem(
    listId: string,
    itemId: string,
    userId: string,
  ): Promise<ListItem> {
    return item(
      await apiPost(itemUrl(listId, itemId, "assign"), { user_id: userId }),
    );
  },
  async respondAssignment(
    listId: string,
    itemId: string,
    accept: boolean,
  ): Promise<ListItem> {
    const tail = `assignment/${accept ? "accept" : "decline"}`;
    return item(await apiPost(itemUrl(listId, itemId, tail)));
  },
  async releaseItem(listId: string, itemId: string): Promise<ListItem> {
    return item(await apiPost(itemUrl(listId, itemId, "release")));
  },
  async unassignItem(listId: string, itemId: string): Promise<ListItem> {
    return item(
      await apiDelete<unknown>(itemUrl(listId, itemId, "assignment")),
    );
  },
  async getActivity(listId: string, p?: PageParams): Promise<ListActivityPage> {
    const r = await apiGet<{ activity: unknown[]; pagination?: Pagination }>(
      `${BASE}/${seg(listId)}/activity${qs(p)}`,
    );
    return {
      entries: r.activity.map(activity),
      nextCursor: next(r.pagination),
    };
  },
  async getMembers(listId: string): Promise<ListMember[]> {
    const r = await apiGet<unknown[]>(`${BASE}/${seg(listId)}/members`);
    return r.map((m) => one<ListMember>(m));
  },
  async addMember(
    listId: string,
    data: ListMemberAddInput,
  ): Promise<ListMember> {
    return one(await apiPost(`${BASE}/${seg(listId)}/members`, snakeize(data)));
  },
  removeMember(listId: string, userId: string): Promise<void> {
    return apiDelete(`${BASE}/${seg(listId)}/members/${seg(userId)}`);
  },
};
