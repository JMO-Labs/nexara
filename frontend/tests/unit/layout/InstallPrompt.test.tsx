/**
 * @file tests/unit/layout/InstallPrompt.test.tsx
 * @brief Install prompt: hidden standalone, iOS steps, native prompt.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { InstallPrompt } from "@/components/layout/InstallPrompt";

const IOS =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1";

function setup(opts: { standalone?: boolean; ua?: string }) {
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: !!opts.standalone && q.includes("standalone"),
    media: q,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
  if (opts.ua)
    Object.defineProperty(navigator, "userAgent", {
      value: opts.ua,
      configurable: true,
    });
}

describe("InstallPrompt", () => {
  afterEach(() => localStorage.clear());

  it("is hidden in standalone mode", () => {
    setup({ standalone: true, ua: IOS });
    render(<InstallPrompt variant="card" />);
    expect(screen.queryByRole("region", { name: "Install app" })).toBeNull();
  });

  it("shows iOS steps on iOS Safari", () => {
    setup({ ua: IOS });
    render(<InstallPrompt variant="card" />);
    fireEvent.click(screen.getByRole("button", { name: "How to install" }));
    expect(
      screen.getByText("Tap Share, then Add to Home Screen."),
    ).toBeInTheDocument();
  });

  it("uses the captured beforeinstallprompt event", async () => {
    setup({ ua: "Mozilla/5.0 (X11; Linux) Chrome/120" });
    render(<InstallPrompt variant="card" />);
    const prompt = vi.fn().mockResolvedValue(undefined);
    const ev = Object.assign(new Event("beforeinstallprompt"), { prompt });
    act(() => void window.dispatchEvent(ev));
    await act(async () =>
      fireEvent.click(await screen.findByRole("button", { name: "Install" })),
    );
    expect(prompt).toHaveBeenCalled();
  });

  it("banner waits for the 3rd visit", () => {
    setup({ ua: IOS });
    localStorage.setItem("nx:visits", "1");
    sessionStorage.clear();
    render(<InstallPrompt variant="banner" />);
    expect(screen.queryByRole("region", { name: "Install app" })).toBeNull();
  });
});
