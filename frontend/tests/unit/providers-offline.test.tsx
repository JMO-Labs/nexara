/**
 * @file tests/unit/providers-offline.test.tsx
 * @brief Providers default queries to offlineFirst and clear on purge event.
 */
import { describe, it, expect } from "vitest";
import { render, act } from "@testing-library/react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import Providers from "@/app/providers";
import { CLEAR_EVENT } from "@/lib/pwa/clearUserCache";

describe("Providers", () => {
  it("uses offlineFirst and empties cache on purge", () => {
    let qc!: QueryClient;
    const Grab = () => {
      qc = useQueryClient();
      return null;
    };
    render(
      <Providers>
        <Grab />
      </Providers>,
    );
    expect(qc.getDefaultOptions().queries?.networkMode).toBe("offlineFirst");
    qc.setQueryData(["feed"], 1);
    act(() => void window.dispatchEvent(new Event(CLEAR_EVENT)));
    expect(qc.getQueryData(["feed"])).toBeUndefined();
  });
});
