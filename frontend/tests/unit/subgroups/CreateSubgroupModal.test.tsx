import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { CreateSubgroupModal } from "@/components/subgroups/CreateSubgroupModal";

// Mock the APIs
vi.mock("@/lib/api/subgroups", () => ({
  getSubgroup: vi.fn(() => Promise.reject(new Error("404"))),
}));

vi.mock("@/lib/api/search", () => ({
  searchAll: vi.fn(() =>
    Promise.resolve({
      items: [],
      next_cursor: null,
      has_more: false,
      totals: {},
    }),
  ),
}));

vi.mock("@/lib/api/media", () => ({
  uploadFile: vi.fn(),
}));

// Mock useMediaUpload
vi.mock("@/hooks/useMediaUpload", () => ({
  useMediaUpload: () => ({
    mutateAsync: vi.fn(async (_file: File) => "mock-media-id"),
    isPending: false,
    progress: 0,
  }),
}));

// Mock useCreateSubgroup
vi.mock("@/hooks/useSubgroups", () => ({
  useCreateSubgroup: () => ({
    mutateAsync: vi.fn(async (_body: unknown) => ({ id: "test-id" })),
    isPending: false,
  }),
}));

const queryClient = new QueryClient();

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("CreateSubgroupModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("auto-generates slug from name", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    const inputs = screen.getAllByRole("textbox");
    const nameInput = inputs[0]; // First input is Name
    const slugInput = inputs[1]; // Second input is Slug

    await user.type(nameInput, "My Cool Group");
    expect(slugInput).toHaveValue("my-cool-group");
  });

  it("stops auto-slug when user manually edits slug field", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    const inputs = screen.getAllByRole("textbox");
    const nameInput = inputs[0];
    const slugInput = inputs[1];

    await user.type(nameInput, "My Group");
    expect(slugInput).toHaveValue("my-group");

    await user.clear(slugInput);
    await user.type(slugInput, "custom-slug");

    // Change name again
    await user.clear(nameInput);
    await user.type(nameInput, "Different Name");

    // Slug should NOT change
    expect(slugInput).toHaveValue("custom-slug");
  });

  it("disables submit when slug format is invalid", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    const inputs = screen.getAllByRole("textbox");
    const nameInput = inputs[0];
    const slugInput = inputs[1];
    const submitButton = screen.getByRole("button", { name: /Create/i });

    await user.type(nameInput, "My Group");
    expect(slugInput).toHaveValue("my-group");

    // Initially valid because auto-generated slug is valid
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
    });

    // Edit slug to invalid format
    await user.clear(slugInput);
    await user.type(slugInput, "-invalid");

    // Submit should be disabled after typing invalid slug
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });
  });

  it("shows helper text for invalid slug format", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    const inputs = screen.getAllByRole("textbox");
    const slugInput = inputs[1];

    await user.type(slugInput, "-nope");

    // Look for the error message
    await waitFor(() => {
      expect(
        screen.getByText(/Must start with a letter or number/i),
      ).toBeInTheDocument();
    });
  });

  it("can upload and show cover image", async () => {
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    const uploadButton = screen.getByRole("button", { name: /Upload cover/i });
    expect(uploadButton).toBeInTheDocument();

    // Verify file input exists
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();
    expect(fileInput.accept).toBe("image/*");
  });

  it("can toggle owner assignment section", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateSubgroupModal open={true} onClose={() => {}} />);

    // Toggle owner assignment should not be visible initially
    expect(
      screen.queryByPlaceholderText(/Search for a user/i),
    ).not.toBeInTheDocument();

    // Click toggle
    const toggleButton = screen.getByRole("button", {
      name: /Assign to someone else/i,
    });
    await user.click(toggleButton);

    // Now search input should be visible
    expect(
      screen.getByPlaceholderText(/Search for a user/i),
    ).toBeInTheDocument();
  });
});
