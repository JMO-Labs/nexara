/**
 * @file tests/unit/settings/DataExport.test.tsx
 * @brief DataExportSection + useDataExport hook tests.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  render,
  screen,
  waitFor,
  renderHook,
  act,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DataExportSection } from "@/components/settings/DataExportSection";
import { useExportStatus, useRequestExport } from "@/hooks/useDataExport";
import * as api from "@/lib/api/dataExport";
import { ApiError } from "@/lib/api/errors";
import { useToasts } from "@/stores/toasts";

vi.mock("@/lib/api/dataExport");

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);

const hours = (h: number) => new Date(Date.now() + h * 3600_000).toISOString();
const row = (over: object = {}) => ({
  id: "e1",
  status: "ready",
  created_at: new Date().toISOString(),
  expires_at: hours(46),
  downloaded_at: null,
  ...over,
});

beforeEach(() => {
  vi.resetAllMocks();
  useToasts.getState().clear();
  vi.mocked(api.listExports).mockResolvedValue([]);
});
afterEach(() => vi.useRealTimers());

describe("DataExportSection", () => {
  it("renders title, explanation and enabled button", async () => {
    render(<DataExportSection />, { wrapper });
    expect(
      screen.getByText("Download My Data", { selector: "h2" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Downloads expire after 48 hours/),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Download My Data" }),
    ).toBeEnabled();
  });

  it("requests an export and shows generating state", async () => {
    vi.mocked(api.requestExport).mockResolvedValue({ export_id: "e1" });
    vi.mocked(api.getExportStatus).mockResolvedValue(
      row({ status: "pending" }) as never,
    );
    render(<DataExportSection />, { wrapper });
    await userEvent.click(
      await screen.findByRole("button", { name: "Download My Data" }),
    );
    expect(api.requestExport).toHaveBeenCalled();
    expect(await screen.findByText(/Generating your data/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Download My Data" }),
    ).toBeDisabled();
  });

  it("shows download link and expiry when ready", async () => {
    vi.mocked(api.listExports).mockResolvedValue([row()] as never);
    vi.mocked(api.getExportStatus).mockResolvedValue(row() as never);
    render(<DataExportSection />, { wrapper });
    const link = await screen.findByRole("link", { name: "Download" });
    expect(link).toHaveAttribute("href", "/api/v1/export/e1/download");
    expect(screen.getByText(/Expires in 4[56] hours/)).toBeInTheDocument();
  });

  it("shows expired message without download link", async () => {
    vi.mocked(api.listExports).mockResolvedValue([
      row({ status: "expired" }),
    ] as never);
    vi.mocked(api.getExportStatus).mockResolvedValue(
      row({ status: "expired" }) as never,
    );
    render(<DataExportSection />, { wrapper });
    expect(await screen.findByText(/export link expired/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Download" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Download My Data" }),
    ).toBeEnabled();
  });

  it("shows failure with retry", async () => {
    vi.mocked(api.listExports).mockResolvedValue([
      row({ status: "failed" }),
    ] as never);
    vi.mocked(api.getExportStatus).mockResolvedValue(
      row({ status: "failed" }) as never,
    );
    render(<DataExportSection />, { wrapper });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("maps 429 to rate-limit message", async () => {
    vi.mocked(api.requestExport).mockRejectedValue(
      new ApiError(429, "rate", "x"),
    );
    render(<DataExportSection />, { wrapper });
    await userEvent.click(
      await screen.findByRole("button", { name: "Download My Data" }),
    );
    expect(await screen.findByText(/one export per day/)).toBeInTheDocument();
  });

  it("maps other errors to generic message", async () => {
    vi.mocked(api.requestExport).mockRejectedValue(new Error("boom"));
    render(<DataExportSection />, { wrapper });
    await userEvent.click(
      await screen.findByRole("button", { name: "Download My Data" }),
    );
    expect(
      await screen.findByText(/Failed to request export/),
    ).toBeInTheDocument();
  });

  it("lists history", async () => {
    vi.mocked(api.listExports).mockResolvedValue([
      row({
        id: "e2",
        status: "expired",
        downloaded_at: new Date().toISOString(),
      }),
    ] as never);
    vi.mocked(api.getExportStatus).mockResolvedValue(
      row({ status: "expired" }) as never,
    );
    render(<DataExportSection />, { wrapper });
    expect(await screen.findByText(/Downloaded on/)).toBeInTheDocument();
  });
});

describe("useDataExport hooks", () => {
  it("useRequestExport returns export_id", async () => {
    vi.mocked(api.requestExport).mockResolvedValue({ export_id: "e9" });
    const { result } = renderHook(() => useRequestExport(), { wrapper });
    let out;
    await act(async () => {
      out = await result.current.mutateAsync();
    });
    expect(out).toEqual({ export_id: "e9" });
  });

  it("useExportStatus polls while processing then stops and toasts", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    vi.mocked(api.getExportStatus)
      .mockResolvedValueOnce(row({ status: "processing" }) as never)
      .mockImplementation(async () => {
        await gate;
        return row({ status: "ready" }) as never;
      });
    const { result } = renderHook(() => useExportStatus("e1", 20), { wrapper });
    await waitFor(() => expect(result.current.data?.status).toBe("processing"));
    release();
    await waitFor(() => expect(result.current.data?.status).toBe("ready"));
    const calls = vi.mocked(api.getExportStatus).mock.calls.length;
    await new Promise((r) => setTimeout(r, 80));
    expect(vi.mocked(api.getExportStatus).mock.calls.length).toBe(calls);
    expect(
      useToasts.getState().items.some((t) => /export is ready/.test(t.message)),
    ).toBe(true);
  });

  it("useExportStatus is idle without id", () => {
    renderHook(() => useExportStatus(null), { wrapper });
    expect(api.getExportStatus).not.toHaveBeenCalled();
  });
});
