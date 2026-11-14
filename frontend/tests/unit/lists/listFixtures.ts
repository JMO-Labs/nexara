/**
 * @file tests/unit/lists/listFixtures.ts
 * @brief Shared fixtures and mutation stubs for list component tests.
 */
import { vi } from "vitest";
import type { List, ListItem } from "@/lib/api/listTypes";

export const fieldSchema = [
  { key: "name", label: "Name", type_key: "text", required: true },
  { key: "done", label: "Packed", type_key: "bool" },
];

export const list: List = {
  id: "l1",
  title: "Camping gear",
  description: "What to bring",
  visibility: "community",
  ownerId: "u1",
  communityId: "c1",
  status: "active",
  color: "#3366ff",
  itemCount: 10,
  completedCount: 3,
  signupCount: 2,
  createdAt: "2026-11-01T00:00:00Z",
  updatedAt: "2026-11-01T00:00:00Z",
  fieldSchema,
};

export const item = (id: string, name: string): ListItem => ({
  id,
  position: 0,
  values: { name, done: true },
  dueAt: "2026-12-01T00:00:00Z",
  completed: false,
});

/** @brief Minimal useMutation result stub. */
export const mut = () => ({
  mutate: vi.fn(),
  mutateAsync: vi.fn().mockResolvedValue({}),
  isPending: false,
});
