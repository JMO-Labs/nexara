/**
 * @file tests/unit/events/EventGalleryLink.test.tsx
 * @brief EventGalleryLink: renders a "View gallery" link only when linked.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EventGalleryLink } from "@/components/events/event-detail/EventGalleryLink";
import { GalleryEventLink } from "@/components/galleries/galleries-page/GalleryEventLink";

describe("EventGalleryLink", () => {
  it("links to the gallery", () => {
    render(<EventGalleryLink galleryId="g-1" />);
    expect(screen.getByRole("link", { name: /view gallery/i })).toHaveAttribute(
      "href",
      "/app/galleries?gallery=g-1",
    );
  });

  it("renders nothing without a gallery", () => {
    const { container } = render(<EventGalleryLink galleryId={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("GalleryEventLink", () => {
  it("shows the linked event", () => {
    render(<GalleryEventLink eventId="e-1" title="Picnic" />);
    expect(screen.getByRole("link", { name: /picnic/i })).toHaveAttribute(
      "href",
      "/app/events?event=e-1",
    );
    expect(screen.getByText(/linked to event/i)).toBeInTheDocument();
  });

  it("renders nothing without an event", () => {
    const { container } = render(<GalleryEventLink eventId={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
