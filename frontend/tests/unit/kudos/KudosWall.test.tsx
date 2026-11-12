/**
 * @file tests/unit/kudos/KudosWall.test.tsx
 * @brief KudosWall: grid, empty state, subgroup filter, sort, load more.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";

const listKudos = vi.fn();
vi.mock("@/lib/api/kudos", () => ({ listKudos: (...a: unknown[]) => listKudos(...a) }));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [{ id: "g1", name: "Chess" }] }),
}));

import { KudosWall } from "@/components/feed/KudosWall";

const k = (id: string, name: string, at: string, sg: string | null = null) => ({
  id,
  recipient_id: id,
  message: `msg-${id}`,
  author_id: "a",
  subgroup_id: sg,
  created_at: at,
  recipient: { id, username: id, display_name: name, avatar_url: null },
});

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      <QueryClientProvider client={qc}>
        <KudosWall />
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("KudosWall", () => {
  it("shows empty state", async () => {
    listKudos.mockResolvedValue({ kudos: [], pagination: { has_more: false } });
    wrap();
    expect(await screen.findByText("No kudos yet")).toBeInTheDocument();
  });

  it("renders newest first, oldest on sort change, and paginates", async () => {
    listKudos
      .mockResolvedValueOnce({
        kudos: [
          k("a", "Ana", "2026-01-02T00:00:00Z"),
          k("b", "Bo", "2026-01-01T00:00:00Z", "g1"),
        ],
        pagination: { next_cursor: "c2", has_more: true },
      })
      .mockResolvedValueOnce({
        kudos: [k("c", "Cy", "2025-12-01T00:00:00Z")],
        pagination: { has_more: false },
      });
    wrap();
    const names = async () =>
      (await screen.findAllByRole("article")).map((a) => a.textContent);
    expect((await names())[0]).toMatch(/Ana/);
    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Cy")).toBeInTheDocument();
    expect(listKudos).toHaveBeenLastCalledWith("c2");
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
    await userEvent.selectOptions(screen.getByLabelText("Sort"), "oldest");
    expect((await names())[0]).toMatch(/Cy/);
    await userEvent.selectOptions(screen.getByLabelText("Group"), "g1");
    expect(await screen.findAllByRole("article")).toHaveLength(1);
  });
});
