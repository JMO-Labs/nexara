"use client";
/**
 * @file app/(auth)/sso-test/page.tsx
 * @brief Popup landing for an admin SSO test login: hands the one-time
 *        result id to the opener (same origin only) and closes.
 */
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/auth/AuthCard";
import { SSO_TEST_MESSAGE } from "@/lib/api/adminOauth";

export default function SsoTestPage() {
  const params = useSearchParams();
  const result = params.get("result");
  // Only the fixed code is forwarded; never echo arbitrary params.
  const error = params.get("error") === "sso_failed" ? "sso_failed" : null;

  useEffect(() => {
    if ((!result && !error) || !window.opener) return;
    window.opener.postMessage(
      error
        ? { type: SSO_TEST_MESSAGE, error }
        : { type: SSO_TEST_MESSAGE, result },
      window.location.origin,
    );
    window.close();
  }, [result, error]);

  return (
    <AuthCard title="SSO test sign-in">
      <p role="status" className="text-sm text-muted">
        {error
          ? "Test sign-in failed. Close this window; details are in the server log."
          : result
            ? "Test finished. If this window stays open, close it and return to the admin page."
            : "No test result."}
      </p>
    </AuthCard>
  );
}
