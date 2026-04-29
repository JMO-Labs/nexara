/**
 * @file tests/unit/components/ui/Carousel.test.tsx
 * @brief Unit tests for the Carousel primitive.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

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
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
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

  it("does not start autoplay when prefers-reduced-motion is reduce", () => {
    // Override matchMedia to report reduced motion
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

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
