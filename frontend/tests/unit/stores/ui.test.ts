/**
 * @file tests/unit/stores/ui.test.ts
 * @brief UI store density default, setter and persistence.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { useUI } from "@/stores/ui";

describe("ui store density", () => {
  beforeEach(() => {
    localStorage.clear();
    useUI.setState(useUI.getInitialState(), true);
  });

  it("defaults to comfortable", () => {
    expect(useUI.getInitialState().density).toBe("comfortable");
    expect(useUI.getState().density).toBe("comfortable");
  });

  it("setDensity updates the store", () => {
    useUI.getState().setDensity("compact");
    expect(useUI.getState().density).toBe("compact");
  });

  it("persists density to localStorage", () => {
    useUI.getState().setDensity("compact");
    const raw = JSON.parse(localStorage.getItem("nx-ui") as string);
    expect(raw.state.density).toBe("compact");
  });

  it("restores persisted density on rehydrate (survives reload)", async () => {
    localStorage.setItem(
      "nx-ui",
      JSON.stringify({ state: { density: "compact" }, version: 0 }),
    );
    await useUI.persist.rehydrate();
    expect(useUI.getState().density).toBe("compact");
  });
});
