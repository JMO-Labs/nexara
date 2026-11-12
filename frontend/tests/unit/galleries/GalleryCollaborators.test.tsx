/**
 * @file tests/unit/galleries/GalleryCollaborators.test.tsx
 * @brief Collaborator list, add and remove controls (owner vs non-owner).
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import { GalleryCollaborators } from "@/components/galleries/galleries-page/GalleryCollaborators";

const add = vi.fn();
const remove = vi.fn();

vi.mock("@/hooks/useGalleries", () => ({
  useCollaborators: () => ({
    data: [
      { gallery_id: "g1", user_id: "u1", invited_by: null, invited_at: "" },
    ],
  }),
  useAddCollaborator: () => ({ mutate: add, isPending: false }),
  useRemoveCollaborator: () => ({ mutate: remove, isPending: false }),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQuery: () => ({
    data: {
      items: [
        { id: "u1", username: "al", display_name: "Alice" },
        { id: "u2", username: "bo", display_name: "Bob" },
      ],
    },
  }),
}));

beforeEach(() => vi.clearAllMocks());

test("lists collaborators by display name", () => {
  render(<GalleryCollaborators galleryId="g1" isOwner />);
  expect(screen.getByText("Alice")).toBeInTheDocument();
});

test("owner can add a member", () => {
  render(<GalleryCollaborators galleryId="g1" isOwner />);
  fireEvent.change(screen.getByLabelText("Member"), {
    target: { value: "u2" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(add).toHaveBeenCalledWith("u2");
});

test("owner can remove a collaborator", () => {
  render(<GalleryCollaborators galleryId="g1" isOwner />);
  fireEvent.click(screen.getByRole("button", { name: "Remove Alice" }));
  expect(remove).toHaveBeenCalledWith("u1");
});

test("non-owner is read-only", () => {
  render(<GalleryCollaborators galleryId="g1" isOwner={false} />);
  expect(screen.getByText("Alice")).toBeInTheDocument();
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByLabelText("Member")).toBeNull();
});
