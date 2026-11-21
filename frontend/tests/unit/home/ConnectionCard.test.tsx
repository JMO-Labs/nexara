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
const sendChatMessage = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/hooks/useChat", () => ({
  useCreateDm: () => ({ mutateAsync, isPending: false }),
  sendChatMessage: (...a: unknown[]) => sendChatMessage(...a),
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
    sendChatMessage.mockReset().mockReturnValue(true);
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
      expect(sendChatMessage).toHaveBeenCalledWith("ch1", "Dinner at 6?"),
    );
    expect(mutateAsync).toHaveBeenCalledWith("u1");
    expect(await screen.findByText(/Sent to Tomás/)).toBeInTheDocument();
    expect(screen.getByLabelText("Message Tomás")).toHaveValue("");
    expect(push).not.toHaveBeenCalled();
  });

  it("keeps the text and warns when chat is offline", async () => {
    sendChatMessage.mockReturnValue(false);
    render(<ConnectionCard person={person} status="" />);
    fireEvent.change(screen.getByLabelText("Message Tomás"), {
      target: { value: "hi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/offline/);
    expect(screen.getByLabelText("Message Tomás")).toHaveValue("hi");
  });

  it("Open chat navigates to the DM", async () => {
    render(<ConnectionCard person={person} status="" />);
    fireEvent.click(screen.getByRole("button", { name: "Open chat" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app/chat/ch1"));
  });
});
