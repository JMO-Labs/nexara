"use client";
/**
 * @file components/expenses/SplitGiftButton.tsx
 * @brief "Split this gift" on a wishlist item: creates or reuses the viewer's
 *        shared-costs ledger tied to that wishlist, then opens it.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Receipt } from "lucide-react";
import { Button } from "@/components/ui";
import { useFeature } from "@/hooks/useFeature";
import { splitGift } from "@/lib/api/expenses";
import { formatApiError } from "@/lib/api/errors";
import { useToasts } from "@/stores/toasts";

/**
 * @param itemId wishlist item id
 * @param name item name (accessible label)
 * @return button, or null when shared expenses are off
 */
export function SplitGiftButton({
  itemId,
  name,
}: {
  itemId: string;
  name: string;
}) {
  const on = useFeature("expenses");
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  if (!on) return null;
  const go = async () => {
    setBusy(true);
    try {
      router.push(`/app/expenses/${(await splitGift(itemId)).id}`);
    } catch (err) {
      useToasts
        .getState()
        .push({ variant: "danger", message: formatApiError(err) });
      setBusy(false);
    }
  };
  return (
    <Button
      size="sm"
      variant="glass"
      loading={busy}
      onClick={go}
      aria-label={`Split ${name} with others`}
    >
      <Receipt className="size-4" aria-hidden /> Split this gift
    </Button>
  );
}
