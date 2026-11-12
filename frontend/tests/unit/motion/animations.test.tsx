/**
 * @file tests/unit/motion/animations.test.tsx
 * @brief Animation suite: variants exist, helper and components honour reduced motion.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { renderHook } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});

import {
  scalePress,
  slideUp,
  fadeInOut,
  useMotionProps,
} from "@/components/ui/motion";
import { Tabs, TabList, Tab, TabPanel } from "@/components/ui/Tabs";
import { ReactionRow } from "@/components/feed/ReactionRow";

beforeEach(() => {
  reduced = false;
});

describe("motion variants", () => {
  it("defines scalePress, slideUp, fadeInOut", () => {
    expect(scalePress.pressed).toBeDefined();
    expect(slideUp.initial).toMatchObject({ y: 12, opacity: 0 });
    expect(fadeInOut.initial).toMatchObject({ opacity: 0 });
  });
});

describe("useMotionProps", () => {
  it("returns variant props normally", () => {
    const { result } = renderHook(() => useMotionProps(slideUp));
    expect(result.current.initial).toBe("initial");
    expect(result.current.variants).toBe(slideUp);
  });
  it("returns empty props under reduced motion", () => {
    reduced = true;
    const { result } = renderHook(() => useMotionProps(slideUp));
    expect(result.current).toEqual({});
  });
});

function tabs() {
  return render(
    <Tabs defaultValue="a">
      <TabList>
        <Tab value="a">A</Tab>
      </TabList>
      <TabPanel value="a">panel</TabPanel>
    </Tabs>,
  );
}

describe("TabPanel", () => {
  it("fades in (starts transparent)", () => {
    tabs();
    expect(screen.getByRole("tabpanel")).toHaveStyle({ opacity: "0" });
  });
  it("skips animation under reduced motion", () => {
    reduced = true;
    tabs();
    expect(screen.getByRole("tabpanel").style.opacity).toBe("");
  });
});

describe("ReactionRow animation", () => {
  const props = {
    reactions: [{ emoji: "👍", count: 1, reacted_by_me: false }],
    commentCount: 0,
    onReact: vi.fn(),
  };
  it("marks chip as animating after click", () => {
    render(<ReactionRow {...props} />);
    const chip = screen.getByRole("button", { name: /👍 reaction/ });
    fireEvent.click(chip);
    expect(chip).toHaveAttribute("data-pressed", "true");
  });
  it("does not animate under reduced motion", () => {
    reduced = true;
    render(<ReactionRow {...props} />);
    const chip = screen.getByRole("button", { name: /👍 reaction/ });
    fireEvent.click(chip);
    expect(chip).not.toHaveAttribute("data-pressed");
    expect(props.onReact).toHaveBeenCalled();
  });
});
