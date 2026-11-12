/**
 * @file tests/unit/galleries/GalleriesPage.test.tsx
 * @brief Load-more pagination in the gallery hub.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { GalleriesPage } from "@/components/galleries/galleries-page/GalleriesPage";
import { listGalleries } from "@/lib/api/galleries";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/api/galleries", () => ({ listGalleries: vi.fn() }));
vi.mock("@/hooks/useGalleries", async (orig) => {
  const real = await orig<typeof import("@/hooks/useGalleries")>();
  return {
    useGalleryList: real.useGalleryList,
    useGalleryListInfinite: real.useGalleryListInfinite,
  };
});
vi.mock("@/components/galleries/GalleryCreateModal", () => ({
  GalleryCreateModal: () => null,
}));
vi.mock("@/components/galleries/galleries-page/GalleryDrawer", () => ({
  GalleryDrawer: () => null,
}));
vi.mock("@/components/galleries/galleries-page/LightboxConnected", () => ({
  LightboxConnected: () => null,
}));
vi.mock("@/components/galleries/GalleryCard", () => ({
  GalleryCard: ({ gallery }: { gallery: { title: string } }) => (
    <div data-testid="card">{gallery.title}</div>
  ),
}));

const g = (id: string) => ({ id, title: `Gallery ${id}` });

test("load more fetches page 2 then disappears", async () => {
  vi.mocked(listGalleries).mockImplementation((async (p?: {
    cursor?: string;
    featured?: boolean;
  }) => {
    if (p?.featured) return { items: [], next_cursor: null, has_more: false };
    return p?.cursor
      ? { items: [g("3")], next_cursor: null, has_more: false }
      : { items: [g("1"), g("2")], next_cursor: "c1", has_more: true };
  }) as never);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <GalleriesPage />
    </QueryClientProvider>,
  );
  const btn = await screen.findByRole("button", { name: "Load more" });
  expect(screen.getAllByTestId("card")).toHaveLength(2);
  expect(screen.getByText("2 collections")).toBeInTheDocument();
  await userEvent.click(btn);
  await waitFor(() => expect(screen.getAllByTestId("card")).toHaveLength(3));
  expect(screen.getByText("Gallery 3")).toBeInTheDocument();
  expect(screen.getByText("3 collections")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
});
