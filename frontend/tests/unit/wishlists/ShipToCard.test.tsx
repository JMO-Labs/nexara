/**
 * @file tests/unit/wishlists/ShipToCard.test.tsx
 * @brief Ship-to card: event link, copy button, hidden-address messages.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShipToCard } from "@/components/wishlists/ShipToCard";

const base = {
  user_id: null,
  event_id: null,
  starts_at: null,
  name: null,
  address: null,
};

describe("ShipToCard", () => {
  it("links an event and offers copy", () => {
    render(
      <ShipToCard
        ship={{
          ...base,
          event_id: "e1",
          name: "Family BBQ",
          address: "Lake Park",
        }}
      />,
    );
    expect(screen.getByRole("link", { name: "Family BBQ" })).toHaveAttribute(
      "href",
      "/app/events?event=e1",
    );
    expect(
      screen.getByRole("button", { name: "Copy shipping address" }),
    ).toBeInTheDocument();
  });

  it("explains a hidden address without revealing where", () => {
    const { rerender } = render(
      <ShipToCard ship={{ ...base, user_id: "u1", name: "Grandma" }} />,
    );
    expect(
      screen.getByText(/Grandma's address isn't shared/),
    ).toBeInTheDocument();
    rerender(<ShipToCard ship={{ ...base, name: "the event" }} />);
    expect(
      screen.getByText("Ask the list owner where to send gifts."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
