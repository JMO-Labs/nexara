/**
 * @file tests/unit/notifications/ListNotificationRenderer.test.tsx
 * @brief List notification renderers: title, details, dismiss, navigate.
 */
import { describe, it, expect, vi } from "vitest";
import { screen, render as rtlRender } from "@testing-library/react";
import type { ReactElement } from "react";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";
import { List, CircleCheck, Check, Clock, User } from "lucide-react";
import userEvent from "@testing-library/user-event";
import {
  ListNotification,
  isListNotificationType,
} from "@/components/notifications/ListNotificationRenderer";

const render = (ui: ReactElement) =>
  rtlRender(
    <NextIntlClientProvider locale="en-US" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  );

const ctx = {
  listId: "L1",
  listName: "My Gift List",
  userName: "Ann",
  inviterName: "Bob",
  itemTitle: "Socks",
};
const mk = (type: string) => ({
  id: "n1",
  type,
  context: ctx,
  createdAt: new Date(Date.now() - 5 * 60_000).toISOString(),
});

const EXPECTED_ICON = {
  "list.item": List,
  "list.signup": CircleCheck,
  "list.completed": Check,
  "list.expiring": Clock,
  "list.member": User,
} as const;

describe("ListNotification", () => {
  it.each(Object.entries(EXPECTED_ICON))(
    "renders the %s icon at 20px",
    (type, Expected) => {
      const { container: ref } = render(<Expected />);
      const refClass = ref.querySelector("svg")!.getAttribute("class");
      const { container } = render(
        <ListNotification
          notification={mk(type)}
          onDismiss={vi.fn()}
          onNavigate={vi.fn()}
          href="/app/lists/L1"
        />,
      );
      const svg = container.querySelector("svg")!;
      expect(svg.getAttribute("class")).toContain(
        refClass!.split(" ").find((c) => c !== "lucide")!,
      );
      expect(svg).toHaveAttribute("width", "20");
      expect(svg).toHaveAttribute("height", "20");
    },
  );

  it.each([
    ["list.item", "New item in My Gift List"],
    ["list.signup", "Ann claimed an item"],
    ["list.completed", "Item marked done"],
    ["list.expiring", "Expires in 1 day"],
    ["list.member", "Added by Bob"],
  ])("renders %s title", (type, title) => {
    render(
      <ListNotification
        notification={mk(type)}
        onDismiss={vi.fn()}
        onNavigate={vi.fn()}
        href="/app/lists/L1"
      />,
    );
    expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByText("5m ago")).toBeInTheDocument();
    expect(screen.getByText("Socks")).toBeInTheDocument();
  });

  it("navigates with listId on row click", async () => {
    const onNavigate = vi.fn();
    render(
      <ListNotification
        notification={mk("list.item")}
        onDismiss={vi.fn()}
        onNavigate={onNavigate}
        href="/app/lists/L1"
      />,
    );
    await userEvent.click(screen.getByText("New item in My Gift List"));
    expect(onNavigate).toHaveBeenCalledWith("L1");
  });

  it("dismiss calls onDismiss(id) without navigating", async () => {
    const onDismiss = vi.fn();
    const onNavigate = vi.fn();
    render(
      <ListNotification
        notification={mk("list.item")}
        onDismiss={onDismiss}
        onNavigate={onNavigate}
        href="/app/lists/L1"
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledWith("n1");
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("detects list types", () => {
    expect(isListNotificationType("list.item")).toBe(true);
    expect(isListNotificationType("mention")).toBe(false);
    expect(isListNotificationType("list.signup")).toBe(true);
  });

  it("uses translated fallbacks when context is empty", () => {
    render(
      <ListNotification
        notification={{ ...mk("list.member"), context: {} }}
        onDismiss={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    expect(screen.getByText("Added by a member")).toBeInTheDocument();
  });
});
