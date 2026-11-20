/**
 * @file tests/unit/photos/PhotosPage.test.tsx
 * @brief PhotosPage: view switching (?view=), sort, upload panel, drawer.
 */
import { render as rtlRender, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { vi } from "vitest";
import { PhotosPage } from "@/components/photos/PhotosPage";

let qc = new QueryClient();
const render = (ui: ReactElement) =>
  rtlRender(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);

const nav = vi.hoisted(() => ({ qs: "", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push }),
  useSearchParams: () => new URLSearchParams(nav.qs),
}));

const hooks = vi.hoisted(() => ({
  list: vi.fn(),
  media: vi.fn(),
}));
vi.mock("@/hooks/useGalleries", () => ({
  useGalleryListInfinite: (p: unknown) => hooks.list(p),
}));
vi.mock("@/hooks/useHomeMedia", () => ({
  useHomeMediaInfinite: (p: unknown) => hooks.media(p),
}));
vi.mock("@/components/photos/AlbumGrid", () => ({
  AlbumGrid: ({ items }: { items?: { title: string }[] }) => (
    <div data-testid="albums">{items?.map((i) => i.title).join(",")}</div>
  ),
}));
vi.mock("@/components/galleries/MediaThumb", () => ({
  MediaThumb: ({ alt }: { alt?: string }) => <span>{alt}</span>,
}));
vi.mock("@/components/media/UploadZone", () => ({
  UploadZone: ({ onComplete }: { onComplete?: (m: unknown) => void }) => (
    <div data-testid="upload-zone">
      <button onClick={() => onComplete?.({ id: "new" })}>finish-upload</button>
    </div>
  ),
}));
vi.mock("@/components/galleries/GalleryCreateModal", () => ({
  GalleryCreateModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="create-modal" /> : null,
}));
vi.mock("@/components/galleries/galleries-page/GalleryDrawer", () => ({
  GalleryDrawer: ({ galleryId }: { galleryId: string | null }) => (
    <div data-testid="drawer">{galleryId}</div>
  ),
}));
vi.mock("@/components/galleries/galleries-page/LightboxConnected", () => ({
  LightboxConnected: () => null,
}));
vi.mock("@/components/galleries/Lightbox", () => ({
  Lightbox: () => <div data-testid="lightbox" />,
}));

const mediaItem = (id: string, title: string) => ({
  media_id: id,
  media: {
    id,
    alt_text: null,
    thumbnail_key: null,
    created_at: new Date().toISOString(),
  },
  source: "gallery",
  source_id: "g1",
  source_title: title,
});

beforeEach(() => {
  qc = new QueryClient();
  nav.qs = "";
  nav.push.mockClear();
  hooks.list.mockReturnValue({
    data: { pages: [{ items: [{ id: "1", title: "Summer" }] }] },
    isLoading: false,
    error: null,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
    refetch: vi.fn(),
  });
  hooks.media.mockReturnValue({
    data: {
      pages: [
        { items: [mediaItem("m1", "Beach day"), mediaItem("m2", "Birthday")] },
      ],
    },
    isLoading: false,
    error: null,
  });
});

describe("PhotosPage", () => {
  it("defaults to the albums view with sort control", () => {
    render(<PhotosPage />);
    expect(screen.getByRole("heading", { name: "Photos" })).toBeInTheDocument();
    expect(screen.getByTestId("albums")).toHaveTextContent("Summer");
    expect(screen.getByRole("radio", { name: "Albums" })).toBeChecked();
    expect(screen.getByRole("combobox", { name: "Sort albums" })).toBeVisible();
  });

  it("phone toolbar drops the giant wrapper pill; sort does not wrap alone", () => {
    render(<PhotosPage />);
    const sort = screen.getByRole("combobox", { name: "Sort albums" });
    const sortPill = sort.parentElement!;
    expect(sortPill).toHaveClass("shrink-0");
    const toolbar = sortPill.parentElement!;
    expect(toolbar).toHaveClass("max-md:rounded-none", "max-md:bg-transparent");
  });

  it("?view=all shows photos and hides sort", () => {
    nav.qs = "view=all";
    render(<PhotosPage />);
    expect(screen.queryByTestId("albums")).toBeNull();
    expect(screen.getByRole("radio", { name: "All photos" })).toBeChecked();
    expect(screen.queryByRole("combobox", { name: "Sort albums" })).toBeNull();
    expect(hooks.media).toHaveBeenCalledWith(60);
    expect(screen.getAllByRole("button", { name: /Open photo/ })).toHaveLength(
      2,
    );
  });

  it("switching view pushes the URL and keeps the gallery param out", async () => {
    nav.qs = "gallery=g1";
    render(<PhotosPage />);
    await userEvent.click(screen.getByRole("radio", { name: "All photos" }));
    expect(nav.push).toHaveBeenCalledWith("/app/photos?view=all");
  });

  it("switching back to albums drops view", async () => {
    nav.qs = "view=all";
    render(<PhotosPage />);
    await userEvent.click(screen.getByRole("radio", { name: "Albums" }));
    expect(nav.push).toHaveBeenCalledWith("/app/photos");
  });

  it("search filters all-photos by title", async () => {
    nav.qs = "view=all";
    render(<PhotosPage />);
    await userEvent.type(screen.getByRole("searchbox"), "beach");
    await waitFor(() =>
      expect(
        screen.getAllByRole("button", { name: /Open photo/ }),
      ).toHaveLength(1),
    );
  });

  it("sort change reaches the albums query", async () => {
    render(<PhotosPage />);
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Sort albums" }),
      "popular",
    );
    expect(hooks.list).toHaveBeenLastCalledWith({
      q: undefined,
      sort: "popular",
    });
  });

  it("Upload photos toggles the upload panel", async () => {
    render(<PhotosPage />);
    expect(screen.queryByTestId("upload-zone")).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Upload photos" }),
    );
    expect(screen.getByTestId("upload-zone")).toBeInTheDocument();
  });

  it("New album opens the create modal", async () => {
    render(<PhotosPage />);
    await userEvent.click(screen.getByRole("button", { name: "New album" }));
    expect(screen.getByTestId("create-modal")).toBeInTheDocument();
  });

  it("?gallery= opens the drawer for that album", () => {
    nav.qs = "gallery=g9";
    render(<PhotosPage />);
    expect(screen.getByTestId("drawer")).toHaveTextContent("g9");
  });

  it("clicking a photo opens the lightbox", async () => {
    nav.qs = "view=all";
    render(<PhotosPage />);
    await userEvent.click(
      screen.getAllByRole("button", { name: /Open photo/ })[0],
    );
    expect(screen.getByTestId("lightbox")).toBeInTheDocument();
  });

  it("upload completion invalidates home media and shows All photos", async () => {
    const spy = vi.spyOn(qc, "invalidateQueries");
    render(<PhotosPage />);
    await userEvent.click(
      screen.getByRole("button", { name: "Upload photos" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "finish-upload" }),
    );
    expect(spy).toHaveBeenCalledWith({ queryKey: ["home-media"] });
    expect(nav.push).toHaveBeenCalledWith("/app/photos?view=all");
  });

  it("All photos pages with Load more", async () => {
    nav.qs = "view=all";
    const fetchNextPage = vi.fn();
    hooks.media.mockReturnValue({
      data: { pages: [{ items: [mediaItem("m1", "Beach day")] }] },
      isLoading: false,
      error: null,
      hasNextPage: true,
      isFetchingNextPage: false,
      fetchNextPage,
    });
    render(<PhotosPage />);
    screen.getByRole("button", { name: "Load more" }).click();
    expect(fetchNextPage).toHaveBeenCalled();
  });

  it("renders upload-sourced items with a fallback title", () => {
    nav.qs = "view=all";
    hooks.media.mockReturnValue({
      data: {
        pages: [
          {
            items: [
              { ...mediaItem("u1", ""), source: "upload", source_title: null },
            ],
          },
        ],
      },
      isLoading: false,
      error: null,
    });
    render(<PhotosPage />);
    expect(
      screen.getByRole("button", { name: "Open photo: Your uploads" }),
    ).toBeInTheDocument();
  });
});
