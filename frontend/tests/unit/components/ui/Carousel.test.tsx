/**
 * @file tests/unit/components/ui/Carousel.test.tsx
 * @brief Unit tests for the Carousel primitive.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock framer-motion useReducedMotion so tests can control it
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return { ...actual, useReducedMotion: vi.fn().mockReturnValue(false) };
});

// Mock embla-carousel-react before importing the component
const mockScrollNext = vi.fn();
const mockScrollPrev = vi.fn();
const mockScrollTo = vi.fn();
const mockCanScrollNext = vi.fn().mockReturnValue(true);
const mockCanScrollPrev = vi.fn().mockReturnValue(true);
const mockSelectedScrollSnap = vi.fn().mockReturnValue(0);
const mockScrollSnapList = vi.fn().mockReturnValue([0, 1, 2]);
const mockOn = vi.fn();
const mockOff = vi.fn();

const mockEmblaApi = {
  scrollNext: mockScrollNext,
  scrollPrev: mockScrollPrev,
  scrollTo: mockScrollTo,
  canScrollNext: mockCanScrollNext,
  canScrollPrev: mockCanScrollPrev,
  selectedScrollSnap: mockSelectedScrollSnap,
  scrollSnapList: mockScrollSnapList,
  on: mockOn,
  off: mockOff,
};

vi.mock("embla-carousel-react", () => ({
  default: vi.fn(() => [vi.fn(), mockEmblaApi]),
}));

import { Carousel } from "@/components/ui/Carousel";

function wrap(ui: React.ReactNode) {
  return render(<>{ui}</>);
}

const slides = [
  <div key="1">Slide 1</div>,
  <div key="2">Slide 2</div>,
  <div key="3">Slide 3</div>,
];

describe("Carousel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockScrollSnapList.mockReturnValue([0, 1, 2]);
    mockSelectedScrollSnap.mockReturnValue(0);
    mockCanScrollNext.mockReturnValue(true);
    mockCanScrollPrev.mockReturnValue(false);
  });

  it("renders all slides into the embla container", () => {
    wrap(<Carousel slides={slides} ariaLabel="Test carousel" />);
    expect(screen.getByText("Slide 1")).toBeInTheDocument();
    expect(screen.getByText("Slide 2")).toBeInTheDocument();
    expect(screen.getByText("Slide 3")).toBeInTheDocument();
  });

  it("renders Previous and Next arrow buttons with correct aria-labels", () => {
    wrap(<Carousel slides={slides} ariaLabel="Test carousel" showArrows />);
    expect(
      screen.getByRole("button", { name: "Previous slide" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Next slide" }),
    ).toBeInTheDocument();
  });

  it("renders dot buttons matching slide count", () => {
    wrap(<Carousel slides={slides} ariaLabel="Test carousel" showDots />);
    const dots = screen.getAllByRole("tab");
    expect(dots).toHaveLength(3);
    expect(dots[0]).toHaveAttribute("aria-label", "Slide 1");
    expect(dots[1]).toHaveAttribute("aria-label", "Slide 2");
    expect(dots[2]).toHaveAttribute("aria-label", "Slide 3");
  });

  it("calls scrollNext when ArrowRight pressed on container", () => {
    wrap(<Carousel slides={slides} ariaLabel="Test carousel" />);
    const container = screen.getByRole("region", { name: "Test carousel" });
    fireEvent.keyDown(container, { key: "ArrowRight" });
    expect(mockScrollNext).toHaveBeenCalledOnce();
  });

  it("calls scrollPrev when ArrowLeft pressed on container", () => {
    wrap(<Carousel slides={slides} ariaLabel="Test carousel" />);
    const container = screen.getByRole("region", { name: "Test carousel" });
    fireEvent.keyDown(container, { key: "ArrowLeft" });
    expect(mockScrollPrev).toHaveBeenCalledOnce();
  });

  it("renders nothing for empty slides array", () => {
    const { container } = wrap(
      <Carousel slides={[]} ariaLabel="Empty carousel" />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("hides arrows and dots for a single slide", () => {
    mockScrollSnapList.mockReturnValue([0]);
    wrap(
      <Carousel
        slides={[<div key="1">Only slide</div>]}
        ariaLabel="Single slide carousel"
        showArrows
        showDots
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Previous slide" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Next slide" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("does not start autoplay when prefers-reduced-motion is reduce", async () => {
    const { useReducedMotion } = await import("framer-motion");
    vi.mocked(useReducedMotion).mockReturnValue(true);

    vi.useFakeTimers();
    wrap(
      <Carousel
        slides={slides}
        ariaLabel="Test carousel"
        autoplay
        autoplayDelayMs={100}
      />,
    );
    vi.advanceTimersByTime(500);
    expect(mockScrollNext).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
