/**
 * @file tests/unit/members/PeopleDirectory.test.tsx
 * @brief People directory: cards, debounced search, filter, load more, states.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, act } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
const mutateAsync = vi.fn();
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync, isPending: false }),
}));

const fetchNextPage = vi.fn();
let state: Record<string, unknown> = {};
const useDirectory = vi.fn<(q: string, f: string) => unknown>(() => state);
vi.mock("@/hooks/useMembers", () => ({
  useDirectory: (q: string, f: string) => useDirectory(q, f),
}));

import MembersPage from "@/app/app/members/page";

const person = (o: Record<string, unknown> = {}) => ({
  user_id: "u1",
  username: "tomas",
  display_name: "Tomás Reyes",
  avatar_url: null,
  online: false,
  last_seen_at: null,
  shared_groups: [{ id: "g1", name: "Family", accent_color: "#112233" }],
  primary_group_id: "g1",
  ...o,
});

const ready = (items: unknown[], hasNextPage = false) => ({
  data: { pages: [{ items }] },
  isLoading: false,
  isError: false,
  hasNextPage,
  isFetchingNextPage: false,
  fetchNextPage,
  refetch: vi.fn(),
});

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  push.mockReset();
  mutateAsync.mockReset();
  fetchNextPage.mockReset();
  useDirectory.mockClear();
  state = ready([person()]);
});
afterEach(() => vi.useRealTimers());

describe("PeopleDirectory", () => {
  it("renders header, card with groups, status and actions", () => {
    state = ready([person({ online: true })]);
    renderWithProviders(<MembersPage />);
    expect(
      screen.getByRole("heading", { name: "People", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Tomás Reyes")).toBeInTheDocument();
    expect(screen.getByText("Online now")).toBeInTheDocument();
    expect(screen.getByText("Family")).toBeInTheDocument();
    expect(screen.queryByText("u1")).toBeNull();
  });

  it("Message opens a DM and Profile navigates", async () => {
    mutateAsync.mockResolvedValue({ id: "c1" });
    renderWithProviders(<MembersPage />);
    fireEvent.click(screen.getByRole("button", { name: /Message Tomás/ }));
    await act(async () => {});
    expect(push).toHaveBeenCalledWith("/app/chat/c1");
    fireEvent.click(
      screen.getByRole("button", { name: /View Tomás.*profile/ }),
    );
    expect(push).toHaveBeenCalledWith("/app/members/u1");
  });

  it("debounces search by 250ms", () => {
    renderWithProviders(<MembersPage />);
    fireEvent.change(screen.getByLabelText("Search people"), {
      target: { value: "tom" },
    });
    expect(useDirectory).not.toHaveBeenCalledWith("tom", "all");
    act(() => {
      vi.advanceTimersByTime(260);
    });
    expect(useDirectory).toHaveBeenCalledWith("tom", "all");
  });

  it("filter segments change the query filter", () => {
    renderWithProviders(<MembersPage />);
    fireEvent.click(screen.getByRole("radio", { name: "Online" }));
    expect(useDirectory).toHaveBeenLastCalledWith("", "online");
    fireEvent.click(screen.getByRole("radio", { name: "My groups" }));
    expect(useDirectory).toHaveBeenLastCalledWith("", "groups");
  });

  it("shows Load more only when another page exists", () => {
    renderWithProviders(<MembersPage />);
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  });

  it("Load more fetches the next page", () => {
    state = ready([person()], true);
    renderWithProviders(<MembersPage />);
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(fetchNextPage).toHaveBeenCalled();
  });

  it("shows empty and loading states", () => {
    state = ready([]);
    const { unmount } = renderWithProviders(<MembersPage />);
    expect(screen.getByText("No one found")).toBeInTheDocument();
    unmount();
    state = { ...ready([]), isLoading: true, data: undefined };
    renderWithProviders(<MembersPage />);
    expect(screen.getByTestId("people-skeleton")).toBeInTheDocument();
  });
});
