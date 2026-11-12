/**
 * @file tests/unit/kudos/KudosComposer.test.tsx
 * @brief KudosComposer: autocomplete recipient, submit, cancel.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";

const listUsers = vi.fn();
const createKudos = vi.fn();
vi.mock("@/lib/api/users", () => ({
  listUsers: (...a: unknown[]) => listUsers(...a),
}));
vi.mock("@/lib/api/kudos", () => ({
  createKudos: (...a: unknown[]) => createKudos(...a),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));

import { KudosComposer } from "@/components/feed/KudosComposer";

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  listUsers.mockResolvedValue({
    items: [
      { id: "u2", username: "ana", display_name: "Ana Lima", avatar_url: null },
      { id: "u3", username: "bo", display_name: "Bo Chen", avatar_url: null },
    ],
    next_cursor: null,
    has_more: false,
  });
  createKudos.mockResolvedValue({ id: "k1" });
});

describe("KudosComposer", () => {
  it("autocompletes, submits and closes", async () => {
    const onClose = vi.fn();
    wrap(<KudosComposer open onClose={onClose} />);
    expect(screen.getByText("Send Kudos")).toBeInTheDocument();
    const send = screen.getByRole("button", { name: "Send" });
    expect(send).toBeDisabled();
    await userEvent.type(screen.getByRole("combobox"), "an");
    await userEvent.click(
      await screen.findByRole("option", { name: /Ana Lima/ }),
    );
    await userEvent.type(screen.getByLabelText("Message (optional)"), "Thanks");
    await userEvent.click(send);
    await waitFor(() =>
      expect(createKudos.mock.calls[0][0]).toEqual({
        recipient_id: "u2",
        message: "Thanks",
      }),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("filters out non-matching users", async () => {
    wrap(<KudosComposer open onClose={vi.fn()} />);
    await userEvent.type(screen.getByRole("combobox"), "bo");
    expect(
      await screen.findByRole("option", { name: /Bo Chen/ }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Ana/ })).toBeNull();
  });

  it("cancel closes without posting", async () => {
    const onClose = vi.fn();
    wrap(<KudosComposer open onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
    expect(createKudos).not.toHaveBeenCalled();
  });
});
