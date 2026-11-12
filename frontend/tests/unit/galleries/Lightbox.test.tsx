/**
 * @file tests/unit/galleries/Lightbox.test.tsx
 * @brief Lightbox keyboard nav, close isolation and image fade-in.
 */
import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Lightbox } from "@/components/galleries/Lightbox";
import type { GalleryItem } from "@/lib/api/galleries";

const items: GalleryItem[] = [
  {
    id: "i1",
    gallery_id: "g1",
    media_id: "m1",
    added_by: "u1",
    caption: "one",
    position: 0,
    created_at: "2026-04-25T00:00:00Z",
  },
  {
    id: "i2",
    gallery_id: "g1",
    media_id: "m2",
    added_by: "u1",
    caption: "two",
    position: 1,
    created_at: "2026-04-25T00:00:00Z",
  },
];

function wrap(ui: React.ReactNode) {
  return render(ui);
}

describe("Lightbox", () => {
  it("Esc fires onClose", () => {
    const onClose = vi.fn();
    wrap(
      <Lightbox
        items={items}
        index={0}
        onClose={onClose}
        onIndexChange={() => {}}
      />,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
  it("ArrowRight advances index", () => {
    const onIdx = vi.fn();
    wrap(
      <Lightbox
        items={items}
        index={0}
        onClose={() => {}}
        onIndexChange={onIdx}
      />,
    );
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(onIdx).toHaveBeenCalledWith(1);
  });
  it("ArrowLeft decrements index", () => {
    const onIdx = vi.fn();
    wrap(
      <Lightbox
        items={items}
        index={1}
        onClose={() => {}}
        onIndexChange={onIdx}
      />,
    );
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(onIdx).toHaveBeenCalledWith(0);
  });
  it("labels the image and traps Tab focus", () => {
    wrap(
      <Lightbox
        items={items}
        index={1}
        onClose={() => {}}
        onIndexChange={() => {}}
      />,
    );
    expect(screen.getByAltText("two")).toBeInTheDocument();
    const close = screen.getByLabelText("Close");
    const prev = screen.getByLabelText("Previous");
    // Next is disabled on the last item, so Previous is the last focusable.
    prev.focus();
    fireEvent.keyDown(window, { key: "Tab" });
    expect(close).toHaveFocus();
  });
});

describe("Lightbox close isolation", () => {
  it("Esc does not propagate to outer listeners", () => {
    const outer = vi.fn();
    document.addEventListener("keydown", outer);
    document.addEventListener("keydown", outer, true);
    const onClose = vi.fn();
    render(
      <Lightbox
        items={items}
        index={0}
        onClose={onClose}
        onIndexChange={vi.fn()}
      />,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(outer).not.toHaveBeenCalled();
    document.removeEventListener("keydown", outer);
    document.removeEventListener("keydown", outer, true);
  });

  it("close button click does not bubble to parents", () => {
    const parent = vi.fn();
    const onClose = vi.fn();
    render(
      <div onClick={parent}>
        <Lightbox
          items={items}
          index={0}
          onClose={onClose}
          onIndexChange={vi.fn()}
        />
      </div>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(parent).not.toHaveBeenCalled();
  });
});

describe("Lightbox image fade", () => {
  const view = (index: number) => (
    <Lightbox
      items={items}
      index={index}
      onClose={() => {}}
      onIndexChange={() => {}}
    />
  );

  it("starts hidden and fades in on load", () => {
    render(view(0));
    const img = screen.getByAltText("one");
    expect(img).toHaveClass("opacity-0");
    fireEvent.load(img);
    expect(img).toHaveClass("opacity-100");
  });

  it("becomes visible when the image fails to load", () => {
    render(view(0));
    const img = screen.getByAltText("one");
    fireEvent.error(img);
    expect(img).toHaveClass("opacity-100");
  });

  it("resets to hidden when the index changes", () => {
    const { rerender } = render(view(0));
    fireEvent.load(screen.getByAltText("one"));
    rerender(view(1));
    expect(screen.getByAltText("two")).toHaveClass("opacity-0");
  });
});
