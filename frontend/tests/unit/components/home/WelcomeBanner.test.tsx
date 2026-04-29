/**
 * @file tests/unit/components/home/WelcomeBanner.test.tsx
 * @brief Unit tests for the WelcomeBanner component.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { WelcomeBanner } from "@/components/home/WelcomeBanner";

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe("WelcomeBanner", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const defaultProps = {
    userName: "Alice",
    newPosts: 5,
    upcomingEvents: 3,
    unreadNotifications: 7,
  };

  it("renders greeting with user name", () => {
    wrap(<WelcomeBanner {...defaultProps} />);
    expect(screen.getByText(/alice/i)).toBeInTheDocument();
  });

  it("renders 3 stat chips with correct aria-labels", () => {
    wrap(<WelcomeBanner {...defaultProps} />);
    expect(
      screen.getByRole("link", { name: /5 new posts/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /3 upcoming events/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /7 unread notifications/i }),
    ).toBeInTheDocument();
  });

  it("renders skeleton when isLoading=true", () => {
    wrap(<WelcomeBanner {...defaultProps} isLoading />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it('shows "Good morning" at 09:00', () => {
    vi.setSystemTime(new Date(2025, 0, 1, 9, 0, 0));
    wrap(<WelcomeBanner {...defaultProps} />);
    expect(screen.getByText(/good morning/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('shows "Good afternoon" at 14:00', () => {
    vi.setSystemTime(new Date(2025, 0, 1, 14, 0, 0));
    wrap(<WelcomeBanner {...defaultProps} />);
    expect(screen.getByText(/good afternoon/i)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('shows "Good evening" at 20:00', () => {
    vi.setSystemTime(new Date(2025, 0, 1, 20, 0, 0));
    wrap(<WelcomeBanner {...defaultProps} />);
    expect(screen.getByText(/good evening/i)).toBeInTheDocument();
    vi.useRealTimers();
  });
});
