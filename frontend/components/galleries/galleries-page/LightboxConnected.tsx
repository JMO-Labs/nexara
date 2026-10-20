"use client";
/**
 * @file components/galleries/galleries-page/LightboxConnected.tsx
 * @brief Lightbox wired to a gallery's items query.
 */
import { Lightbox } from "@/components/galleries/Lightbox";
import { useGalleryItems } from "@/hooks/useGalleries";

/**
 * @brief Render the lightbox once items load.
 * @param galleryId gallery whose items to show
 * @param index current item index
 * @param onClose close handler
 * @param onIndexChange navigation handler
 * @return lightbox or null
 */
export function LightboxConnected({
  galleryId,
  index,
  onClose,
  onIndexChange,
}: {
  galleryId: string;
  index: number;
  onClose: () => void;
  onIndexChange: (i: number) => void;
}) {
  const { data: items } = useGalleryItems(galleryId);
  if (!items || items.length === 0) return null;
  return (
    <Lightbox
      items={items}
      index={index}
      onClose={onClose}
      onIndexChange={onIndexChange}
    />
  );
}
