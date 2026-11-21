/**
 * @file tests/unit/chat/ChatRouteLayout.test.tsx
 * @brief Chat route wrapper leaves room for the real TopBar and a bottom gutter.
 */
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import ChatRouteLayout from "@/app/app/chat/layout";

describe("ChatRouteLayout", () => {
  it("uses a 5rem desktop offset and a bottom gutter", () => {
    const { container } = render(
      <ChatRouteLayout>
        <span>x</span>
      </ChatRouteLayout>,
    );
    const cls = (container.firstElementChild as HTMLElement).className;
    expect(cls).toContain("md:h-[calc(100dvh-5rem)]");
    expect(cls).not.toContain("md:h-[calc(100dvh-3.5rem)]");
    expect(cls).toContain("pb-4");
  });
});
