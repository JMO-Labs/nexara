"use client";
/**
 * @file components/admin/SsoTab.tsx
 * @brief OAuth provider management tab for SSO configuration.
 */
import { useState } from "react";
import { AlertCircle, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import {
  useOauthProviders,
  useCreateOauthProvider,
  useUpdateOauthProvider,
  useToggleOauthProvider,
  useDeleteOauthProvider,
  useDiscoverIssuer,
  useSsoOnly,
  useSetSsoOnly,
} from "@/hooks/useAdminOauth";
import { Button, IconButton, Modal, Switch } from "@/components/ui";
import { useConfirmDialog } from "@/stores/confirmDialog";
import type {
  OAuthProviderCreate,
  OAuthProviderResponse,
} from "@/lib/api/adminOauth";
import { SsoProviderForm } from "./SsoProviderForm";

/**
 * @brief SSO providers admin tab.
 * @return tab content
 */
export function SsoTab() {
  const [openModal, setOpenModal] = useState(false);
  const [editing, setEditing] = useState<OAuthProviderResponse | null>(null);
  const confirm = useConfirmDialog((s) => s.confirm);

  const { data: providers, isLoading, error } = useOauthProviders();
  const { data: ssoOnly } = useSsoOnly();
  const setSsoOnly = useSetSsoOnly();
  const createMutation = useCreateOauthProvider();
  const updateMutation = useUpdateOauthProvider();
  const toggleMutation = useToggleOauthProvider();
  const deleteMutation = useDeleteOauthProvider();
  const discoverMutation = useDiscoverIssuer();

  const closeModal = () => {
    setOpenModal(false);
    setEditing(null);
  };

  const handleSubmit = (v: OAuthProviderCreate, secretChanged: boolean) => {
    if (editing) {
      const { client_secret, ...rest } = v;
      updateMutation.mutate({
        providerId: editing.id,
        updates: secretChanged ? { ...rest, client_secret } : rest,
      });
    } else {
      createMutation.mutate(v);
    }
    closeModal();
  };

  const handleDelete = async (p: OAuthProviderResponse) => {
    const ok = await confirm({
      title: `Delete ${p.display_name}?`,
      message:
        "Are you sure? Users won't be able to log in with this provider.",
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (ok) deleteMutation.mutate(p.id);
  };

  const noneActive = !providers?.some((p) => p.enabled);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2
          role="status"
          aria-label="Loading providers"
          className="size-6 motion-safe:animate-spin"
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-2xl border-l-4 border-danger bg-surface p-3"
      >
        Failed to load OAuth providers
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <label className="flex min-h-11 items-center gap-2 font-medium">
            <Switch
              checked={!!ssoOnly}
              onCheckedChange={(v) => setSsoOnly.mutate(v)}
              aria-label="SSO only"
            />
            SSO only
          </label>
          {ssoOnly && (
            <p className="text-sm text-muted">
              Require all users to log in via SSO
            </p>
          )}
        </div>
        <Button onClick={() => setOpenModal(true)}>
          <Plus className="size-4" aria-hidden="true" />
          Add OIDC Provider
        </Button>
      </div>
      {ssoOnly && noneActive && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-2xl border-l-4 border-danger bg-surface p-3"
        >
          <AlertCircle className="size-4" aria-hidden="true" />
          SSO-only is enabled but no providers are active. Users can&apos;t log
          in!
        </div>
      )}

      {providers && providers.length > 0 ? (
        <ul className="grid gap-4 md:grid-cols-2">
          {providers.map((provider) => (
            <li
              key={provider.id}
              className="flex flex-col gap-3 rounded-2xl bg-surface p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold">
                    {provider.display_name}
                  </h3>
                  <p className="truncate text-sm text-muted">
                    {provider.issuer}
                  </p>
                </div>
                <span className="text-sm text-muted">
                  {provider.provider_type.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <label className="flex min-h-11 items-center gap-2 text-sm">
                  <Switch
                    checked={provider.enabled}
                    onCheckedChange={() => toggleMutation.mutate(provider.id)}
                    aria-label={`Toggle ${provider.display_name}`}
                  />
                  {provider.enabled ? "Enabled" : "Disabled"}
                </label>
                <div className="flex gap-1">
                  <IconButton
                    variant="ghost"
                    aria-label={`Edit ${provider.display_name}`}
                    onClick={() => setEditing(provider)}
                  >
                    <Pencil className="size-4" aria-hidden="true" />
                  </IconButton>
                  <IconButton
                    variant="ghost"
                    aria-label={`Delete ${provider.display_name}`}
                    onClick={() => handleDelete(provider)}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </IconButton>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div role="status" className="rounded-2xl bg-surface p-3">
          No OAuth providers configured yet
        </div>
      )}

      <Modal
        open={openModal || !!editing}
        onClose={closeModal}
        title={editing ? "Edit OIDC provider" : "Add OIDC provider"}
      >
        <SsoProviderForm
          key={editing?.id ?? "new"}
          provider={editing}
          pending={createMutation.isPending || updateMutation.isPending}
          onCancel={closeModal}
          onSubmit={handleSubmit}
          onTest={(url) => discoverMutation.mutateAsync(url)}
        />
      </Modal>
    </div>
  );
}
