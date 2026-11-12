/**
 * @file tests/unit/admin/PromptsTab.test.tsx
 * @brief Tests for PromptsTab component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as usePromptsModule from "@/hooks/usePrompts";
import { PromptsTab } from "@/components/admin/PromptsTab";
import type { PromptResponse } from "@/lib/api/prompts";

vi.mock("@/hooks/usePrompts");

describe("PromptsTab", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "Wrapper";
  const wrapper = Wrapper;

  const mockPrompts: PromptResponse[] = [
    {
      id: "prompt-1",
      title: "Holiday memory",
      body: "What is your favorite holiday memory?",
      source: "custom",
      is_enabled: true,
      frequency_type: "annual_date",
      trigger_month: 12,
      trigger_day: 1,
      trigger_weekday: null,
      trigger_week_interval: null,
      trigger_month_day: null,
      trigger_custom_rule: null,
      trigger_one_time_date: null,
      active_days: 7,
      scope: "community",
      subgroup_id: null,
      notify_members: true,
      notification_body: null,
      linked_event_id: null,
      generate_summary: true,
      prompt_type: "standard",
      interest_category_slug: null,
      interest_capture_hint: null,
      created_by: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  ];

  it("should render prompt list", async () => {
    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: mockPrompts,
    } as any);

    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Holiday memory")).toBeInTheDocument();
    });
  });

  it("should toggle enabled state", async () => {
    const updateMutation = {
      mutate: vi.fn(),
      isPending: false,
    };

    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: mockPrompts,
    } as any);

    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue(
      updateMutation as any,
    );

    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    const user = userEvent.setup();
    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Holiday memory")).toBeInTheDocument();
    });

    const switches = screen.getAllByRole("switch");
    if (switches.length > 0) {
      await user.click(switches[0]);

      await waitFor(() => {
        expect(updateMutation.mutate).toHaveBeenCalled();
      });
    }
  });

  it("should render empty state when no prompts", async () => {
    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: [],
    } as any);

    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/no prompts yet/i)).toBeInTheDocument();
    });
  });

  it("should send is_enabled when toggled", async () => {
    const updateMutation = { mutate: vi.fn(), isPending: false };
    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: mockPrompts,
    } as any);
    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue(
      updateMutation as any,
    );
    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    const user = userEvent.setup();
    render(<PromptsTab />, { wrapper });
    await user.click(screen.getAllByRole("switch")[0]);

    expect(updateMutation.mutate).toHaveBeenCalledWith({
      promptId: "prompt-1",
      payload: { is_enabled: false },
    });
  });

  it("should not offer seeding builtin prompts", async () => {
    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: [],
    } as any);
    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<PromptsTab />, { wrapper });

    expect(
      screen.queryByRole("button", { name: /seed builtin library/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /new prompt/i }),
    ).toBeInTheDocument();
  });
});
