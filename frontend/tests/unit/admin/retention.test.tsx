/**
 * @file tests/unit/admin/retention.test.tsx
 * @brief Tests for retention policy validation and the admin row/tab.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/retention";
import {
  POLICY_META,
  validateDays,
  type RetentionPolicy,
} from "@/lib/retention-policies";
import { RetentionPolicyRow } from "@/components/admin/RetentionPolicyRow";
import { RetentionTab } from "@/components/admin/RetentionTab";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));
vi.mock("@/lib/api/retention");

const pol = (over: Partial<RetentionPolicy> = {}): RetentionPolicy => ({
  policy_key: "chat_messages",
  enabled: true,
  retention_days: 365,
  delete_media_files: false,
  updated_at: "2026-01-01T00:00:00Z",
  updated_by: null,
  ...over,
});

describe("validateDays", () => {
  it("enforces chat minimum of 30", () => {
    expect(validateDays("chat_messages", 10)).toMatch(/30/);
    expect(validateDays("chat_messages", 30)).toBeNull();
  });
  it("enforces soft-deleted post minimum of 7", () => {
    expect(validateDays("soft_deleted_posts", 6)).toMatch(/7/);
  });
  it("allows keep-forever only where permitted", () => {
    expect(validateDays("post_age", null)).toBeNull();
    expect(validateDays("chat_messages", null)).not.toBeNull();
  });
  it("rejects non-integers", () => {
    expect(validateDays("chat_messages", 40.5)).not.toBeNull();
  });
  it("defines all 12 policies", () => {
    expect(Object.keys(POLICY_META)).toHaveLength(12);
  });
});

describe("RetentionPolicyRow", () => {
  it("blocks save and shows error below minimum", async () => {
    const onSave = vi.fn();
    render(
      <RetentionPolicyRow policy={pol()} onSave={onSave} saving={false} />,
    );
    const input = screen.getByLabelText(/Chat Messages retention days/i);
    await userEvent.clear(input);
    await userEvent.type(input, "5");
    expect(screen.getByText(/at least 30/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /save chat messages/i }),
    ).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("submits edited values", async () => {
    const onSave = vi.fn();
    render(
      <RetentionPolicyRow policy={pol()} onSave={onSave} saving={false} />,
    );
    const input = screen.getByLabelText(/Chat Messages retention days/i);
    await userEvent.clear(input);
    await userEvent.type(input, "100");
    await userEvent.click(
      screen.getByRole("switch", { name: /Chat Messages enabled/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /save chat messages/i }),
    );
    expect(onSave).toHaveBeenCalledWith("chat_messages", {
      enabled: false,
      retention_days: 100,
      delete_media_files: false,
    });
  });

  it("shows keep forever for null days", () => {
    render(
      <RetentionPolicyRow
        policy={pol({
          policy_key: "post_age",
          enabled: false,
          retention_days: null,
        })}
        onSave={vi.fn()}
        saving={false}
      />,
    );
    expect(screen.getByText(/keep forever/i)).toBeInTheDocument();
  });

  it("shows danger warning for opt-in policies", () => {
    render(
      <RetentionPolicyRow
        policy={pol({
          policy_key: "post_age",
          enabled: false,
          retention_days: null,
        })}
        onSave={vi.fn()}
        saving={false}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/permanently delete/i);
  });
});

describe("RetentionTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
  });
  const wrap = () => {
    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    return render(
      <QueryClientProvider client={qc}>
        <RetentionTab />
      </QueryClientProvider>,
    );
  };

  it("renders a row per policy and saves via PUT", async () => {
    vi.mocked(api.listRetentionPolicies).mockResolvedValue(
      Object.keys(POLICY_META).map((k) =>
        pol({ policy_key: k, retention_days: 60 }),
      ),
    );
    vi.mocked(api.updateRetentionPolicy).mockResolvedValue(pol());
    wrap();
    await screen.findByText("Notifications");
    expect(screen.getAllByRole("row")).toHaveLength(13);
    await userEvent.click(
      screen.getByRole("switch", { name: /Notifications enabled/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: /save notifications/i }),
    );
    await waitFor(() =>
      expect(api.updateRetentionPolicy).toHaveBeenCalledWith("notifications", {
        enabled: false,
        retention_days: 60,
        delete_media_files: false,
      }),
    );
    await waitFor(() => expect(useToasts.getState().items.length).toBe(1));
  });

  it("shows an error notice on load failure", async () => {
    vi.mocked(api.listRetentionPolicies).mockRejectedValue(new Error("x"));
    wrap();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /failed to load/i,
    );
  });
});
