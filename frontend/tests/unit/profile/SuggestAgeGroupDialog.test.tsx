/**
 * @file tests/unit/profile/SuggestAgeGroupDialog.test.tsx
 * @brief Suggest dialog posts the payload; own profile has no suggest action.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const client = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  seg: (s: string) => s,
}));
vi.mock("@/lib/api/client", () => client);

import { SuggestAgeGroupDialog } from "@/components/profile/SuggestAgeGroupDialog";

describe("SuggestAgeGroupDialog", () => {
  it("posts subject_id, age_group and note", async () => {
    client.apiPost.mockResolvedValue({});
    const onClose = vi.fn();
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <SuggestAgeGroupDialog
          open
          onClose={onClose}
          subjectId="u1"
          name="Sam"
        />
      </QueryClientProvider>,
    );
    fireEvent.change(screen.getByLabelText(/note/i), {
      target: { value: "Looks 15" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send suggestion/i }));
    await waitFor(() =>
      expect(client.apiPost).toHaveBeenCalledWith(
        "/api/v1/age-groups/suggestions",
        { subject_id: "u1", age_group: "adult", note: "Looks 15" },
      ),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});
