"use client";
/**
 * @file components/layout/ModalRoot.tsx
 * @brief Single mount point for app-wide overlays: command palette,
 *        imperative modals (driven by useModals), toasts.
 *        Handles create-post, create-event, create-gallery modal keys.
 */
import dynamic from "next/dynamic";
import { GlobalCommandPalette } from "@/components/search/GlobalCommandPalette";
import { ToastRoot } from "@/components/ui/Toast";
import { Modal } from "@/components/ui/Modal";
import { useModals } from "@/stores/modals";

// Lazy-loaded so the shell does not pull in heavy feature modules at load.
const PostComposer = dynamic(
  () => import("@/components/feed/PostComposer").then((m) => m.PostComposer),
  { ssr: false },
);
const EventCreateModal = dynamic(
  () =>
    import("@/components/events/EventCreateModal").then(
      (m) => m.EventCreateModal,
    ),
  { ssr: false },
);
const GalleryCreateModal = dynamic(
  () =>
    import("@/components/galleries/GalleryCreateModal").then(
      (m) => m.GalleryCreateModal,
    ),
  { ssr: false },
);

export function ModalRoot() {
  const open = useModals((s) => s.open);
  const close = useModals((s) => s.close);

  return (
    <>
      <GlobalCommandPalette />
      <ToastRoot />

      {/* create-post */}
      <Modal open={open === "create-post"} onClose={close} title="New post">
        <PostComposer onPosted={close} />
      </Modal>

      {/* create-event */}
      {open === "create-event" && <EventCreateModal open onClose={close} />}

      {/* create-gallery */}
      {open === "create-gallery" && <GalleryCreateModal open onClose={close} />}
    </>
  );
}
