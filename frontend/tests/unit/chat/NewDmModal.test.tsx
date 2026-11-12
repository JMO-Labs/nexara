/**
 * @file tests/unit/chat/NewDmModal.test.tsx
 * @brief NewDmModal: open, search, select member, exclude self.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { NewDmModal } from "@/components/chat/NewDmModal";
import { listUsers } from "@/lib/api/users";
import { renderWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/users", () => ({ listUsers: vi.fn() }));

const users = [
  { id: "u1", username: "alice", display_name: "Alice A", avatar_url: null },
  { id: "u2", username: "bob", display_name: "Bob B", avatar_url: null },
  { id: "u3", username: "carol", display_name: "Carol C", avatar_url: null },
];

function setup(props: Partial<Parameters<typeof NewDmModal>[0]> = {}) {
  const onClose = vi.fn();
  const onSelect = vi.fn();
  renderWithProviders(
    <NewDmModal open onClose={onClose} onSelect={onSelect} {...props} />,
  );
  return { onClose, onSelect };
}

describe("NewDmModal", () => {
  beforeEach(() => {
    vi.mocked(listUsers).mockReset();
    vi.mocked(listUsers).mockResolvedValue({
      items: users,
      next_cursor: null,
      has_more: false,
    });
  });

  it("lists members when open", async () => {
    setup();
    expect(await screen.findByText("Alice A")).toBeInTheDocument();
    expect(screen.getByLabelText("Search members")).toBeInTheDocument();
    expect(listUsers).toHaveBeenCalledWith(null, 100);
  });

  it("does not fetch when closed", () => {
    renderWithProviders(
      <NewDmModal open={false} onClose={vi.fn()} onSelect={vi.fn()} />,
    );
    expect(listUsers).not.toHaveBeenCalled();
  });

  it("filters by query and shows empty state", async () => {
    setup();
    await screen.findByText("Alice A");
    const input = screen.getByLabelText("Search members");
    fireEvent.change(input, { target: { value: "bob" } });
    expect(screen.queryByText("Alice A")).not.toBeInTheDocument();
    expect(screen.getByText("Bob B")).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "zzz" } });
    expect(screen.getByText("No matching users.")).toBeInTheDocument();
  });

  it("selecting a member calls onSelect with id and closes", async () => {
    const { onSelect, onClose } = setup();
    fireEvent.click(await screen.findByText("Carol C"));
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith("u3"));
    expect(onClose).toHaveBeenCalled();
  });

  it("hides the excluded user", async () => {
    setup({ excludeUserId: "u1" });
    await screen.findByText("Bob B");
    expect(screen.queryByText("Alice A")).not.toBeInTheDocument();
  });
});
