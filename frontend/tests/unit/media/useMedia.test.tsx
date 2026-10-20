/**
 * @file tests/unit/media/useMedia.test.tsx
 * @brief useUpload uses singleUpload for small files via uploadFile path.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "toasts.media.uploaded": "Upload complete",
      "toasts.errors.generic": "Something went wrong",
    };
    return translations[key] || key;
  },
}));

vi.mock("@/lib/api/media", () => ({
  uploadFile: vi.fn(),
  getMedia: vi.fn(),
  deleteMedia: vi.fn(),
}));

import * as api from "@/lib/api/media";
import { useUpload } from "@/hooks/useMedia";

describe("useUpload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  it("calls uploadFile and resolves the media item", async () => {
    (api.uploadFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "m1",
    });
    const { result } = renderHook(() => useUpload());
    const file = new File([new Uint8Array(100)], "a.png", {
      type: "image/png",
    });
    let returned: unknown;
    await act(async () => {
      returned = await result.current.upload(file);
    });
    expect(api.uploadFile).toHaveBeenCalledWith(file, expect.any(Function));
    expect((returned as { id: string }).id).toBe("m1");
    await waitFor(() => expect(result.current.uploading).toBe(false));
  });
});
