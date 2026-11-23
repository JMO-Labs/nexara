/**
 * @file tests/unit/stories/StoriesAsked.test.tsx
 * @brief Outgoing asks: answered links to the post; declined (shown as open) reads Waiting.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const list = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/stories", () => ({ listStoryRequests: list }));

import { StoriesAsked } from "@/components/stories/StoriesAsked";

const req = (o: object) => ({
  id: "r",
  asker: { id: "me", display_name: "Me" },
  teller: { id: "t", display_name: "Ruth" },
  question: "First job?",
  status: "open",
  post_id: null,
  created_at: new Date().toISOString(),
  expires_at: new Date().toISOString(),
  ...o,
});

function show(outgoing: object[]) {
  list.mockResolvedValue({ incoming: [], outgoing });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <StoriesAsked />
    </QueryClientProvider>,
  );
}

describe("StoriesAsked", () => {
  it("answered shows a link to the post", async () => {
    show([req({ status: "answered", post_id: "p9" })]);
    const a = await screen.findByRole("link", { name: /listen/i });
    expect(a).toHaveAttribute("href", "/app/post/p9");
    expect(screen.getByText(/Ruth/)).toBeInTheDocument();
  });

  it("an open (formerly declined) request reads Waiting", async () => {
    show([req({ status: "open" })]);
    expect(await screen.findByText("Waiting")).toBeInTheDocument();
    expect(screen.queryByText(/declin/i)).toBeNull();
  });

  it("empty state offers to ask", async () => {
    show([]);
    expect(
      await screen.findByText("You haven't asked anyone for a story yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Ask for a story" }),
    ).toHaveAttribute("href", "/app/members");
  });
});
