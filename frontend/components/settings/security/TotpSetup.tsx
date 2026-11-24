"use client";
/**
 * @file components/settings/security/TotpSetup.tsx
 * @brief Authenticator enrolment dialog: QR + secret, then a 6-digit confirm.
 */
import { useEffect, useState, type FormEvent } from "react";
import QRCode from "qrcode";
import { Button, Input, Modal } from "@/components/ui";
import { totpConfirm, totpStart } from "@/lib/api/twoFactor";
import { formatApiError } from "@/lib/api/errors";
import { refreshAccessToken } from "@/lib/auth/session";

export interface TotpSetupProps {
  onClose: () => void;
  /** Called with the recovery codes once TOTP is enabled. */
  onEnabled: (codes: string[]) => void;
}

/**
 * @brief TOTP setup dialog (mount it to open; unmount to reset).
 * @param props see TotpSetupProps
 * @return modal
 */
export function TotpSetup({ onClose, onEnabled }: TotpSetupProps) {
  const [qr, setQr] = useState<string | null>(null);
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let off = false;
    totpStart()
      .then(async (r) => {
        const url = await QRCode.toDataURL(r.otpauth_uri);
        if (off) return;
        setSecret(r.secret);
        setQr(url);
      })
      .catch((e) => !off && setError(formatApiError(e)));
    return () => {
      off = true;
    };
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await totpConfirm(code.trim());
      await refreshAccessToken();
      onEnabled(r.recovery_codes);
    } catch (err) {
      setError(formatApiError(err, "Code rejected."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Set up authenticator"
      description="Scan the QR code with an authenticator app, then enter the 6-digit code."
      size="sm"
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {qr && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={qr}
            alt="QR code for authenticator app"
            width={192}
            height={192}
            className="mx-auto rounded-lg bg-white p-2"
          />
        )}
        {secret && (
          <p className="text-sm">
            Cannot scan? Enter this key:{" "}
            <code className="break-all font-mono">{secret}</code>{" "}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => navigator.clipboard?.writeText(secret)}
            >
              Copy key
            </Button>
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Input
          label="6-digit code"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={8}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <Button
          type="submit"
          loading={busy}
          disabled={!qr || code.trim().length < 6}
        >
          Turn on
        </Button>
      </form>
    </Modal>
  );
}
