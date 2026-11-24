"use client";
/**
 * @file components/settings/SecurityTab.tsx
 * @brief Settings › Security: authenticator app, recovery codes, passkeys.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { SettingsRow } from "@/components/ui/SettingsRow";
import {
  getTwoFactorStatus,
  regenerateRecovery,
  totpDisable,
} from "@/lib/api/twoFactor";
import { refreshAccessToken } from "@/lib/auth/session";
import { PasskeyList } from "./security/PasskeyList";
import { ProofDialog } from "./security/ProofDialog";
import { RecoveryCodes } from "./security/RecoveryCodes";
import { TotpSetup } from "./security/TotpSetup";

const STATUS = ["2fa", "status"];

/**
 * @brief Disable-dialog body: a code-shaped value (6 digits or an 8-char
 *        recovery code) is sent as both password and code; the server tries
 *        the password first, then the code.
 * @param v trimmed input
 * @return totpDisable body
 */
export const disableProof = (v: string) => {
  const code = v.replace(/[\s-]/g, "");
  return /^(\d{6}|[A-Za-z0-9]{8})$/.test(code)
    ? { password: v, code }
    : { password: v };
};

/** @brief Security settings tab. */
export function SecurityTab() {
  const qc = useQueryClient();
  const [setup, setSetup] = useState(false);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [proof, setProof] = useState<"regen" | "disable" | null>(null);
  const status = useQuery({ queryKey: STATUS, queryFn: getTwoFactorStatus });
  const refresh = () => qc.invalidateQueries({ queryKey: STATUS });
  const regen = useMutation({ mutationFn: regenerateRecovery });
  const s = status.data;

  return (
    <Panel className="flex max-w-[880px] flex-col">
      {s?.required && !s.totp && s.passkeys === 0 && (
        <p role="status" className="mb-2 text-sm font-medium text-destructive">
          Your admin requires two-step sign-in. Set up an authenticator or a
          passkey below.
        </p>
      )}
      <SettingsRow
        label="Authenticator app"
        description="Use a 6-digit code from an app like Aegis or Google Authenticator when you sign in."
      >
        {s?.totp ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm">On</span>
            <Button variant="ghost" onClick={() => setProof("disable")}>
              Turn off
            </Button>
          </div>
        ) : (
          <Button onClick={() => setSetup(true)}>Set up authenticator</Button>
        )}
      </SettingsRow>
      {s?.totp && (
        <SettingsRow
          label="Recovery codes"
          description={`${s.recovery_left} unused codes left.`}
        >
          <Button variant="ghost" onClick={() => setProof("regen")}>
            Regenerate codes
          </Button>
        </SettingsRow>
      )}
      <SettingsRow
        label="Passkeys"
        description="Sign in with your fingerprint, face or a security key."
      >
        <PasskeyList />
      </SettingsRow>

      {setup && (
        <TotpSetup
          onClose={() => setSetup(false)}
          onEnabled={(c) => {
            setSetup(false);
            setCodes(c);
            refresh();
          }}
        />
      )}
      <RecoveryCodes codes={codes} onDone={() => setCodes(null)} />
      <ProofDialog
        open={proof === "regen"}
        title="Regenerate recovery codes"
        label="Code or recovery code"
        confirmLabel="Regenerate"
        onClose={() => setProof(null)}
        onSubmit={async (code) => {
          const r = await regen.mutateAsync(code);
          setCodes(r.recovery_codes);
          refresh();
        }}
      />
      <ProofDialog
        open={proof === "disable"}
        title="Turn off authenticator"
        label="Password, code or recovery code"
        confirmLabel="Turn off"
        type="password"
        onClose={() => setProof(null)}
        onSubmit={async (v) => {
          await totpDisable(disableProof(v));
          await refreshAccessToken();
          refresh();
        }}
      />
    </Panel>
  );
}
