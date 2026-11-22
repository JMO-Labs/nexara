"use client";
/**
 * @file components/admin/FeaturesTab.tsx
 * @brief Admin Features tab: one switch per feature, grouped by area.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Switch } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import {
  getFeatures,
  putFeatures,
  type FeatureKey,
  type Features,
} from "@/lib/api/features";
import { FEATURES_KEY } from "@/hooks/useFeature";
import { AdminLoading } from "./AdminState";

const GROUPS: { title: string; items: [FeatureKey, string, string][] }[] = [
  {
    title: "Daily habits",
    items: [
      ["recap", "Weekly recap email", "A Sunday email of what you missed."],
      ["on_this_day", "On this day", "Memories from past years."],
      ["daily_question", "Daily question", "One question a day for everyone."],
      ["time_capsules", "Time capsules", "Sealed notes that open later."],
    ],
  },
  {
    title: "Share and plan",
    items: [
      ["event_albums", "Event albums", "Photo albums for each event."],
      ["recipes", "Recipes", "A shared recipe box."],
      ["memorials", "Memorials", "Remember members who have passed."],
      ["expenses", "Shared expenses", "Track who owes whom."],
      ["rides", "Ride sharing", "Offer and request rides to events."],
      ["chores", "Chore rotation", "Repeating chores that take turns."],
    ],
  },
  {
    title: "Connection",
    items: [
      ["relations", "Family relations", "Say how members are related."],
      ["family_tree", "Family tree", "A tree view built from relations."],
      [
        "reconnect_nudges",
        "Reconnect nudges",
        "Private reminders to reach out.",
      ],
      ["safe_arrival", "Safe arrival", "Tell watchers you made it."],
      ["voice_stories", "Voice stories", "Record answers to story questions."],
    ],
  },
  {
    title: "Access",
    items: [
      ["simple_mode", "Simple mode", "Larger text and fewer menus."],
      ["newsletter", "Monthly newsletter", "A printable monthly page."],
      [
        "reply_by_email",
        "Reply by email",
        "Let people answer notification emails. Needs mail settings.",
      ],
    ],
  },
];

/** @brief Feature switches; each change saves that one key. */
export function FeaturesTab() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const { data } = useQuery({ queryKey: FEATURES_KEY, queryFn: getFeatures });
  const save = useMutation({
    mutationFn: (patch: Partial<Features>) => putFeatures(patch),
    onSuccess: (d) => qc.setQueryData(FEATURES_KEY, d),
    onError: (err) => push({ variant: "danger", message: formatApiError(err) }),
  });
  if (!data) return <AdminLoading />;
  return (
    <div className="flex flex-col gap-4">
      {GROUPS.map((g) => (
        <Panel key={g.title} title={g.title} className="flex flex-col gap-3">
          {g.items.map(([key, label, hint]) => (
            <div key={key} className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-medium">{label}</p>
                <p className="text-muted text-sm">{hint}</p>
              </div>
              <Switch
                aria-label={label}
                checked={data[key]}
                disabled={save.isPending}
                onCheckedChange={(v) => save.mutate({ [key]: v })}
              />
            </div>
          ))}
        </Panel>
      ))}
    </div>
  );
}
