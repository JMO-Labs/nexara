/**
 * @file tests/unit/stores/ui.test.ts
 * @brief UI store density default, setter and persistence.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { useUI } from "@/stores/ui";

describe("ui store density", () => {
  beforeEach(() => {
    localStorage.clear();
    useUI.setState({ density: "comfortable" });
  });

  it("defaults to comfortable", () => {
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
});
