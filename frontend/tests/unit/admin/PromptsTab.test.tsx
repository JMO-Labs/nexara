/**
 * @file tests/unit/admin/PromptsTab.test.tsx
 * @brief Tests for PromptsTab component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import * as usePromptsModule from '@/hooks/usePrompts';
import { PromptsTab } from '@/components/admin/PromptsTab';
import type { PromptResponse } from '@/lib/api/prompts';

vi.mock('@/hooks/usePrompts');

describe('PromptsTab', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient();
    vi.clearAllMocks();
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'Wrapper';
  const wrapper = Wrapper;

  const mockPrompts: PromptResponse[] = [
    {
      id: 'prompt-1',
      title: 'Holiday memory',
      body: 'What is your favorite holiday memory?',
      frequency: 'annual_date',
      trigger_month: 12,
      trigger_day: 1,
      enabled: true,
      prompt_type: 'standard',
      created_at: new Date('2024-01-01'),
      updated_at: new Date('2024-01-01'),
      response_count: 5,
    },
  ];

  it('should render prompt list', async () => {
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

    vi.mocked(usePromptsModule.useSeedBuiltinPrompts).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Holiday memory')).toBeInTheDocument();
    });
  });

  it('should toggle enabled state', async () => {
    const updateMutation = {
      mutate: vi.fn(),
      isPending: false,
    };

    vi.mocked(usePromptsModule.usePrompts).mockReturnValue({
      isLoading: false,
      data: mockPrompts,
    } as any);

    vi.mocked(usePromptsModule.useUpdatePrompt).mockReturnValue(updateMutation as any);

    vi.mocked(usePromptsModule.useCreatePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useDeletePrompt).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    vi.mocked(usePromptsModule.useSeedBuiltinPrompts).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    const user = userEvent.setup();
    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Holiday memory')).toBeInTheDocument();
    });

    const switches = screen.getAllByRole('switch');
    if (switches.length > 0) {
      await user.click(switches[0]);

      await waitFor(() => {
        expect(updateMutation.mutate).toHaveBeenCalled();
      });
    }
  });

  it('should render empty state when no prompts', async () => {
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

    vi.mocked(usePromptsModule.useSeedBuiltinPrompts).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);

    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/no prompts yet/i)).toBeInTheDocument();
    });
  });

  it('should call seed when Seed builtin library clicked', async () => {
    const seedMutation = {
      mutate: vi.fn(),
      isPending: false,
    };

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

    vi.mocked(usePromptsModule.useSeedBuiltinPrompts).mockReturnValue(seedMutation as any);

    const user = userEvent.setup();
    render(<PromptsTab />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/no prompts yet/i)).toBeInTheDocument();
    });

    const seedButton = screen.getByRole('button', { name: /seed builtin library/i });
    await user.click(seedButton);

    await waitFor(() => {
      expect(seedMutation.mutate).toHaveBeenCalled();
    });
  });
});
