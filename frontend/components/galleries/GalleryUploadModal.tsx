"use client";
/**
 * @file components/galleries/GalleryUploadModal.tsx
 * @brief Two-step modal: gallery selector + uploader.
 */
import * as React from "react";
import {
  Modal,
  Input,
  Textarea,
  Select,
  Option,
  Button,
} from "@/components/ui";
import { GalleryUpload } from "./GalleryUpload";
import { useGalleryList, useCreateGallery } from "@/hooks/useGalleries";

export interface GalleryUploadModalProps {
  open: boolean;
  onClose: () => void;
  subgroupId: string;
}

export function GalleryUploadModal({
  open,
  onClose,
  subgroupId,
}: GalleryUploadModalProps) {
  const create = useCreateGallery();
  const { data: galleriesData } = useGalleryList({ subgroup_id: subgroupId });

  const [step, setStep] = React.useState<"select" | "upload">("select");
  const [selectedGalleryId, setSelectedGalleryId] = React.useState<
    string | null
  >(null);
  const [showNewGalleryForm, setShowNewGalleryForm] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");

  const galleries = galleriesData?.items ?? [];

  const handleCreateAndUpload = async () => {
    if (!title.trim()) return;
    try {
      const result = await create.mutateAsync({
        title,
        description: description || null,
        visibility: "subgroup",
        subgroup_id: subgroupId,
      });
      setSelectedGalleryId(result.id);
      setTitle("");
      setDescription("");
      setShowNewGalleryForm(false);
      setStep("upload");
    } catch (err) {
      console.error("Failed to create gallery", err);
    }
  };

  const handleSelectExisting = (galleryId: string) => {
    setSelectedGalleryId(galleryId);
    setStep("upload");
  };

  const handleClose = () => {
    setStep("select");
    setSelectedGalleryId(null);
    setShowNewGalleryForm(false);
    setTitle("");
    setDescription("");
    onClose();
  };

  const actions = "flex justify-end gap-2";
  return (
    <Modal open={open} onClose={handleClose} title="Upload media">
      {step === "select" ? (
        <div className="flex flex-col gap-4">
          {!showNewGalleryForm ? (
            <>
              <Select
                label="Select a gallery"
                placeholder="Select a gallery"
                value={selectedGalleryId ?? ""}
                onValueChange={(v) => {
                  if (v === "new") setShowNewGalleryForm(true);
                  else if (v) handleSelectExisting(v);
                }}
              >
                {galleries.map((g) => (
                  <Option key={g.id} value={g.id}>
                    {g.title}
                  </Option>
                ))}
                <Option value="new">Create new gallery</Option>
              </Select>
              <div className={actions}>
                <Button variant="ghost" onClick={handleClose}>
                  Cancel
                </Button>
              </div>
            </>
          ) : (
            <>
              <Input
                label="Gallery title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="e.g. Summer 2026"
              />
              <Textarea
                label="Description"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
              />
              <div className={actions}>
                <Button
                  variant="ghost"
                  onClick={() => setShowNewGalleryForm(false)}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  loading={create.isPending}
                  onClick={handleCreateAndUpload}
                  disabled={!title.trim()}
                >
                  Create & upload
                </Button>
              </div>
            </>
          )}
        </div>
      ) : selectedGalleryId ? (
        <div className="flex flex-col gap-4">
          <GalleryUpload galleryId={selectedGalleryId} />
          <div className={actions}>
            <Button variant="ghost" onClick={handleClose}>
              Done
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

export default GalleryUploadModal;
