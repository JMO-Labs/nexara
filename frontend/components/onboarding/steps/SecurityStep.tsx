"use client";
/**
 * @file components/onboarding/steps/SecurityStep.tsx
 * @brief Wizard step 6: authenticator app and passkeys.
 */
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui";
import { PasskeyList } from "@/components/settings/security/PasskeyList";
import { RecoveryCodes } from "@/components/settings/security/RecoveryCodes";
import { TotpSetup } from "@/components/settings/security/TotpSetup";
import { getTwoFactorStatus } from "@/lib/api/twoFactor";

const STATUS = ["2fa", "status"];

export function SecurityStep({ required }: { required: boolean }) {
  const qc = useQueryClient();
  const [setup, setSetup] = React.useState(false);
  const [codes, setCodes] = React.useState<string[] | null>(null);
  const status = useQuery({ queryKey: STATUS, queryFn: getTwoFactorStatus });
  const s = status.data;
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        {required
          ? "Your admin requires two-step sign-in. Set up an authenticator app or a passkey."
          : "Add a second step to keep your account safe."}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {s?.totp ? (
          <span className="text-sm">Authenticator app is on</span>
        ) : (
          <Button onClick={() => setSetup(true)}>Set up authenticator</Button>
        )}
      </div>
      <PasskeyList />
      {setup && (
        <TotpSetup
          onClose={() => setSetup(false)}
          onEnabled={(c) => {
            setSetup(false);
            setCodes(c);
            void qc.invalidateQueries({ queryKey: STATUS });
          }}
        />
      )}
      <RecoveryCodes codes={codes} onDone={() => setCodes(null)} />
    </div>
  );
}
