/**
 * @file lib/api/listTypes.ts
 * @brief camelCase TypeScript types for lists, items, members, signups and
 *        templates, plus snake_case mappers for the backend wire format.
 */

export type ListVisibility = "community" | "subgroup" | "private" | "members";
export type FieldSchema = Record<string, unknown>[];

export interface List {
  id: string;
  title: string;
  description?: string | null;
  visibility: string;
  ownerId: string;
  communityId: string;
  templateId?: string | null;
  subgroupId?: string | null;
  status: string;
  expiresAt?: string | null;
  color?: string | null;
  itemCount: number;
  completedCount: number;
  signupCount: number;
  createdAt: string;
  updatedAt: string;
  fieldSchema: FieldSchema;
}

export interface ListItem {
  id: string;
  position: number;
  values: Record<string, unknown>;
  dueAt?: string | null;
  completed: boolean;
  completedBy?: string | null;
  completedAt?: string | null;
  lat?: number | null;
  lon?: number | null;
  signupQuantityNeeded?: number | null;
}

export interface ListMember {
  listId: string;
  userId: string;
  role: string;
  sharePersonal: boolean;
  addedAt: string;
}

export interface ListItemSignup {
  itemId: string;
  userId: string;
  quantity: number;
  note?: string | null;
  claimedAt: string;
}

export interface ListTemplateField {
  id?: string;
  key: string;
  label: string;
  typeKey: string;
  required?: boolean;
  position: number;
  config?: Record<string, unknown>;
}

export interface ListTemplateItem {
  id?: string;
  position: number;
  values: Record<string, unknown>;
}

export interface ListTemplate {
  id: string;
  name: string;
  description?: string | null;
  category?: string | null;
  icon?: string | null;
  color?: string | null;
  coverMediaId?: string | null;
  isShared: boolean;
  createdAt: string;
  updatedAt: string;
  fields: ListTemplateField[];
  items: ListTemplateItem[];
}

export type ListPage = { lists: List[]; nextCursor?: string };
export type ListItemPage = { items: ListItem[]; nextCursor?: string };
export type ListTemplatePage = {
  templates: ListTemplate[];
  nextCursor?: string;
};

export interface ListCreateInput {
  title: string;
  description?: string | null;
  visibility?: ListVisibility;
  subgroupId?: string | null;
  fieldSchema?: FieldSchema;
  color?: string | null;
}
export interface ListUpdateInput {
  title?: string;
  description?: string | null;
  color?: string | null;
  expiresAt?: string | null;
}
export interface ListItemCreateInput {
  position: number;
  values?: Record<string, unknown>;
}
export interface ListItemUpdateInput {
  values: Record<string, unknown>;
}
export interface SignupClaimInput {
  quantity?: number;
  note?: string | null;
}
export interface ListMemberAddInput {
  userId: string;
  role?: "viewer" | "editor";
}
export interface ListTemplateInput {
  name: string;
  description?: string | null;
  category?: string | null;
  icon?: string | null;
  color?: string | null;
  isShared?: boolean;
  fields?: ListTemplateField[];
  items?: ListTemplateItem[];
}
export interface ListTemplateCloneInput {
  title?: string;
  visibility?: "community" | "subgroup" | "private";
  includeItems?: boolean;
}

const toCamelKey = (k: string) =>
  k.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
const toSnakeKey = (k: string) =>
  k.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);

const mapKeys = (
  o: object,
  fn: (k: string) => string,
): Record<string, unknown> =>
  Object.fromEntries(Object.entries(o).map(([k, v]) => [fn(k), v]));

/** Shallow snake_case -> camelCase; nested JSON payloads (values, config, fieldSchema rows) stay untouched. */
export const camelize = <T>(o: unknown): T =>
  mapKeys(o as object, toCamelKey) as T;

/** Shallow camelCase -> snake_case for request bodies. */
export const snakeize = (o: object): Record<string, unknown> =>
  mapKeys(o, toSnakeKey);
