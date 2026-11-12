/**
 * @file tests/unit/galleries/GalleryCollaborators.test.tsx
 * @brief GalleryCollaborators: list by display name, owner add/remove,
 *        read-only for others.
 */
import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, beforeEach, test, expect } from "vitest";
import { GalleryCollaborators } from "@/components/galleries/galleries-page/GalleryCollaborators";
import * as galleriesApi from "@/lib/api/galleries";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/api/galleries", () => ({
  listCollaborators: vi.fn(),
  addCollaborator: vi.fn(),
  removeCollaborator: vi.fn(),
}));

vi.mock("@/lib/api/users", () => ({
  listUsers: vi.fn().mockResolvedValue({
    items: [
      { id: "u1", username: "o", display_name: "Ola Ode", avatar_url: null },
      { id: "u2", username: "ann", display_name: "Ann Lee", avatar_url: null },
      { id: "u3", username: "bo", display_name: "Bo Diaz", avatar_url: null },
    ],
    next_cursor: null,
    has_more: false,
  }),
}));

const api = vi.mocked(galleriesApi);

const collab = (user_id: string) => ({
  gallery_id: "g1",
  user_id,
  invited_by: "u1",
  invited_at: "2026-01-01",
});

function renderIt(isOwner: boolean) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GalleryCollaborators galleryId="g1" ownerId="u1" isOwner={isOwner} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.listCollaborators.mockResolvedValue([collab("u2")]);
  api.addCollaborator.mockResolvedValue(collab("u3"));
  api.removeCollaborator.mockResolvedValue({ message: "ok" });
});

test("lists collaborators by display name", async () => {
  renderIt(false);
  expect(await screen.findByText("Ann Lee")).toBeInTheDocument();
});

test("owner adds a collaborator via select + Add", async () => {
  renderIt(true);
  await screen.findByText("Ann Lee");
  const select = await screen.findByLabelText("Add contributor");
  expect(
    await screen.findByRole("option", { name: "Bo Diaz" }),
  ).toBeInTheDocument();
  // Existing collaborators and the owner are not offered.
  expect(screen.queryByRole("option", { name: "Ann Lee" })).toBeNull();
  expect(screen.queryByRole("option", { name: "Ola Ode" })).toBeNull();
  await userEvent.selectOptions(select, "u3");
  await userEvent.click(screen.getByRole("button", { name: "Add" }));
  await waitFor(() =>
    expect(api.addCollaborator).toHaveBeenCalledWith("g1", "u3"),
  );
});

test("owner removes a collaborator", async () => {
  renderIt(true);
  await userEvent.click(
    await screen.findByRole("button", { name: "Remove Ann Lee" }),
  );
  await waitFor(() =>
    expect(api.removeCollaborator).toHaveBeenCalledWith("g1", "u2"),
  );
});

test("non-owner sees no add/remove controls", async () => {
  renderIt(false);
  await screen.findByText("Ann Lee");
  expect(screen.queryByLabelText("Add contributor")).toBeNull();
  expect(screen.queryByRole("button", { name: "Add" })).toBeNull();
  expect(screen.queryByRole("button", { name: /^Remove/ })).toBeNull();
});
