"use client";
/**
 * @file components/layout/ModalRoot.tsx
 * @brief Single mount point for app-wide overlays: command palette,
 *        imperative modals (driven by useModals), toasts.
 *        Handles create-post, create-event, create-gallery modal keys.
 */
import * as React from "react";
import { GlobalCommandPalette } from "@/components/search/GlobalCommandPalette";
import { ToastRoot } from "@/components/ui/Toast";
import { Modal } from "@/components/ui/Modal";
import { PostComposer } from "@/components/feed/PostComposer";
import { EventCreateModal } from "@/components/events/EventCreateModal";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";
import { useModals } from "@/stores/modals";

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
      <EventCreateModal open={open === "create-event"} onClose={close} />

      {/* create-gallery */}
      <GalleryCreateModal open={open === "create-gallery"} onClose={close} />
    </>
  );
}
