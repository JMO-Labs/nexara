/**
 * @file components/wishlists/wizard/draft.ts
 * @brief Wizard draft state and its mapping to/from the API.
 */
import type { ProfileLevel } from "@/lib/profile";
import type { Occasion } from "@/lib/occasions";
import type {
  RecipientIn,
  RegistryLink,
  ShipTo,
  WishlistDetail,
  WishlistInput,
} from "@/lib/api/wishlists";

/** @brief A picked recipient with a display name for chips. */
export type PickedRecipient = RecipientIn & { label: string };

export interface Draft {
  occasion: Occasion;
  occasion_label: string;
  title: string;
  recipients: PickedRecipient[];
  event_date: string;
  due_by: string;
  currency: string;
  budget_min_cents: number | null;
  budget_max_cents: number | null;
  event_budget_cents: number | null;
  giver_cap_cents: number | null;
  hide_claims: boolean;
  visibility: ProfileLevel;
  note: string;
  registry_links: RegistryLink[];
  ship_mode: "none" | "user" | "event" | "text";
  ship_to_text: string;
  ship_to_user_id: string;
  ship_to_event_id: string;
}

/** @brief Which ship-to kind a saved list uses. */
function shipMode(s?: ShipTo | null): Draft["ship_mode"] {
  if (s?.user_id) return "user";
  if (s?.event_id) return "event";
  return s?.address ? "text" : "none";
}

/** @brief Fresh draft (or one prefilled from an existing list). */
export function initialDraft(
  w?: WishlistDetail | null,
  me?: PickedRecipient,
): Draft {
  return {
    occasion: w?.occasion ?? "birthday",
    occasion_label: w?.occasion_label ?? "",
    title: w?.title ?? "",
    recipients: w
      ? w.recipients.map((r) => ({
          kind: r.kind,
          ref_id: r.ref_id,
          name: r.name,
          label: r.name,
        }))
      : me
        ? [me]
        : [],
    event_date: w?.event_date ?? "",
    due_by: w?.due_by ?? "",
    currency: w?.currency ?? "USD",
    budget_min_cents: w?.budget_min_cents ?? null,
    budget_max_cents: w?.budget_max_cents ?? null,
    event_budget_cents: w?.event_budget_cents ?? null,
    giver_cap_cents: w?.giver_cap_cents ?? null,
    hide_claims: w?.hide_claims ?? true,
    visibility: w?.visibility ?? "groups",
    note: w?.note ?? "",
    registry_links: w?.registry_links ?? [],
    ship_mode: shipMode(w?.ship_to),
    ship_to_text:
      shipMode(w?.ship_to) === "text" ? (w?.ship_to?.address ?? "") : "",
    ship_to_user_id: w?.ship_to?.user_id ?? "",
    ship_to_event_id: w?.ship_to?.event_id ?? "",
  };
}

/** @brief First problem with the draft, or null. */
export function draftError(d: Draft, step: number): string | null {
  if (step >= 0 && !d.title.trim()) return "Give the list a title.";
  if (step >= 1 && d.recipients.length === 0)
    return "Pick who the list is for.";
  if (step >= 2) {
    if (d.due_by && d.event_date && d.due_by > d.event_date)
      return "The buy-by date should be on or before the event.";
    const lo = d.budget_min_cents;
    const hi = d.budget_max_cents;
    if (lo != null && hi != null && lo > hi)
      return "The budget minimum is above the maximum.";
    if (d.registry_links.some((r) => r.url && !/^https?:\/\//i.test(r.url)))
      return "Registry links must start with http:// or https://";
    if (d.ship_mode === "user" && !d.ship_to_user_id)
      return "Pick who gifts ship to.";
    if (d.ship_mode === "event" && !d.ship_to_event_id)
      return "Pick the event.";
    if (d.ship_mode === "text" && !d.ship_to_text.trim())
      return "Add the shipping address.";
  }
  return null;
}

/** @brief Draft as the API body. */
export function toInput(d: Draft): WishlistInput {
  return {
    title: d.title.trim(),
    occasion: d.occasion,
    occasion_label: d.occasion_label.trim() || null,
    event_date: d.event_date || null,
    due_by: d.due_by || null,
    note: d.note.trim() || null,
    visibility: d.visibility,
    currency: d.currency,
    budget_min_cents: d.budget_min_cents,
    budget_max_cents: d.budget_max_cents,
    event_budget_cents: d.event_budget_cents,
    giver_cap_cents: d.giver_cap_cents,
    hide_claims: d.hide_claims,
    registry_links: d.registry_links
      .filter((r) => r.url.trim())
      .map((r) => ({ label: r.label.trim() || "Registry", url: r.url.trim() })),
    ship_to_text: d.ship_mode === "text" ? d.ship_to_text.trim() : null,
    ship_to_user_id: d.ship_mode === "user" ? d.ship_to_user_id : null,
    ship_to_event_id: d.ship_mode === "event" ? d.ship_to_event_id : null,
    recipients: d.recipients.map(({ kind, ref_id, name }) => ({
      kind,
      ref_id,
      name,
    })),
  };
}
