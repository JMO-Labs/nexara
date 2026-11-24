"use client";
/**
 * @file components/admin/SecurityPolicy.tsx
 * @brief Admin "Security" tab: who must use two-step sign-in.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Option, Select } from "@/components/ui/Select";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import {
  getSecurityPolicy,
  putSecurityPolicy,
  type Require2fa,
} from "@/lib/api/twoFactor";
import { AdminLoading, AdminNotice } from "./AdminState";

const KEY = ["admin", "security"];

/** @brief Two-step sign-in policy picker. */
export function SecurityPolicy() {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const q = useQuery({ queryKey: KEY, queryFn: getSecurityPolicy });
  const save = useMutation({
    mutationFn: putSecurityPolicy,
    onSuccess: (d) => {
      qc.setQueryData(KEY, d);
      push({ variant: "success", message: "Security policy saved" });
    },
    onError: (e) => push({ variant: "danger", message: formatApiError(e) }),
  });
  if (q.isError)
    return (
      <AdminNotice tone="error">Failed to load security policy</AdminNotice>
    );
  if (!q.data) return <AdminLoading />;
  return (
    <Panel className="max-w-[880px]">
      <SettingsRow
        label="Require two-step sign-in"
        description="Members get a grace period to set up an authenticator or passkey."
      >
        <Select
          label="Require two-step sign-in"
          value={q.data.require_2fa}
          disabled={save.isPending}
          onValueChange={(v) => save.mutate(v as Require2fa)}
        >
          <Option value="off">Off</Option>
          <Option value="admins">Admins only</Option>
          <Option value="everyone">Everyone</Option>
        </Select>
      </SettingsRow>
    </Panel>
  );
}
