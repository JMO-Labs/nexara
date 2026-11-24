"use client";
/**
 * @file components/onboarding/steps/NotifyStep.tsx
 * @brief Wizard step 5: push notifications for this device and how often the
 *        family digest email arrives.
 */
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PushDevices } from "@/components/settings/PushDevices";
import { RecapSetting } from "@/components/settings/RecapSetting";
import { PREFS_KEY } from "@/components/settings/SnoozeControls";
import { getPreferences, patchPreferences } from "@/lib/api/notifications";
import type { RecapCadence } from "@/lib/notifications/types";

export function NotifyStep() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: PREFS_KEY, queryFn: getPreferences });
  const [cadence, setCadence] = React.useState<RecapCadence | null>(null);
  const change = (c: RecapCadence) => {
    setCadence(c);
    void patchPreferences({ recap_cadence: c }).finally(() =>
      qc.invalidateQueries({ queryKey: PREFS_KEY }),
    );
  };
  return (
    <div className="space-y-4">
      <PushDevices />
      <div>
        <h2 className="mb-1 text-sm font-medium">Email digest</h2>
        <RecapSetting
          value={cadence ?? data?.recap_cadence ?? "weekly"}
          onChange={change}
        />
      </div>
    </div>
  );
}
