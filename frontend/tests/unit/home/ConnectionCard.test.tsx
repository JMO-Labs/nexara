/**
 * @file tests/unit/home/ConnectionCard.test.tsx
 * @brief ConnectionCard: quick message sends into the DM without navigating.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { renderWithProviders as render } from "../../utils/renderWithProviders";
import { ConnectionCard } from "@/components/home/ConnectionCard";
import type { HomePerson } from "@/lib/api/home";

const push = vi.fn();
const mutateAsync = vi.fn();
const postChatMessage = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync, isPending: false }),
}));
const rels = vi.hoisted(() => ({ list: [] as unknown[] }));
vi.mock("@/hooks/useRelations", () => ({
  useRelations: () => ({ data: rels.list }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => true }));
vi.mock("@/stores/session", () => ({
  useSession: (sel: (s: { user: { id: string } }) => unknown) =>
    sel({ user: { id: "me" } }),
}));
vi.mock("@/lib/api/chat", () => ({
  postChatMessage: (...a: unknown[]) => postChatMessage(...a),
}));

const person = {
  user_id: "u1",
  display_name: "Tomás Reyes",
  shared_groups: [],
  shared_events_30d: 0,
} as unknown as HomePerson;

describe("ConnectionCard", () => {
  beforeEach(() => {
    push.mockReset();
    postChatMessage.mockReset().mockResolvedValue({ id: "m1" });
    mutateAsync.mockReset().mockResolvedValue({ id: "ch1" });
  });

  it("quick message sends to the DM and stays on Home", async () => {
    render(<ConnectionCard person={person} status="" />);
    const send = screen.getByRole("button", { name: "Send" });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Message Tomás"), {
      target: { value: "  Dinner at 6?  " },
    });
    fireEvent.click(send);
    await waitFor(() =>
      expect(postChatMessage).toHaveBeenCalledWith("ch1", "Dinner at 6?"),
    );
    expect(mutateAsync).toHaveBeenCalledWith("u1");
    expect(await screen.findByText(/Sent to Tomás/)).toBeInTheDocument();
    expect(screen.getByLabelText("Message Tomás")).toHaveValue("");
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps the text and warns when sending fails", async () => {
    postChatMessage.mockRejectedValue(new Error("down"));
    render(<ConnectionCard person={person} status="" />);
    fireEvent.change(screen.getByLabelText("Message Tomás"), {
      target: { value: "hi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Couldn't send/);
    expect(screen.getByLabelText("Message Tomás")).toHaveValue("hi");
  });

  it("Open chat navigates to the DM", async () => {
    render(<ConnectionCard person={person} status="" />);
    fireEvent.click(screen.getByRole("button", { name: "Open chat" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app/chat/ch1"));
  });

  it("offers to add how you know them when there is no relation", () => {
    rels.list = [];
    const onRelate = vi.fn();
    render(<ConnectionCard person={person} status="" onRelate={onRelate} />);
    fireEvent.click(
      screen.getByRole("button", { name: "Add how you know Tomás" }),
    );
    expect(onRelate).toHaveBeenCalled();
  });

  it("shows a confirmed relation instead of the prompt", () => {
    rels.list = [
      {
        id: "r1",
        status: "confirmed",
        kind: "parent",
        display: "grandmother",
        direction: null,
        person: { id: "u1", type: "user" },
      },
    ];
    render(<ConnectionCard person={person} status="" onRelate={vi.fn()} />);
    expect(screen.getByText("Your grandmother")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Add how you know/ }),
    ).toBeNull();
    rels.list = [];
  });
});
