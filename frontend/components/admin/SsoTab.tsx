"use client";
/**
 * @file components/admin/SsoTab.tsx
 * @brief OAuth provider management tab for SSO configuration.
 */
import { useState } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import {
  useOauthProviders,
  useCreateOauthProvider,
  useToggleOauthProvider,
  useDeleteOauthProvider,
  useDiscoverIssuer,
} from "@/hooks/useAdminOauth";
import { Button, IconButton, Input, Modal, Switch } from "@/components/ui";

/**
 * @brief SSO providers admin tab.
 * @return tab content
 */
export function SsoTab() {
  const [openModal, setOpenModal] = useState(false);
  const [issuerUrl, setIssuerUrl] = useState("");
  const [slug, setSlug] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");

  const { data: providers, isLoading, error } = useOauthProviders();
  const createMutation = useCreateOauthProvider();
  const toggleMutation = useToggleOauthProvider();
  const deleteMutation = useDeleteOauthProvider();
  const discoverMutation = useDiscoverIssuer();

  const handleDiscoverIssuer = async () => {
    if (!issuerUrl) return;
    try {
      await discoverMutation.mutateAsync(issuerUrl);
    } catch (err) {
      console.error("Discovery failed:", err);
    }
  };

  const handleCreateProvider = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      slug,
      display_name: displayName,
      provider_type: "oidc",
      client_id: clientId,
      client_secret: clientSecret,
      issuer: issuerUrl,
    });
    setOpenModal(false);
    setIssuerUrl("");
    setSlug("");
    setDisplayName("");
    setClientId("");
    setClientSecret("");
  };

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
      <div className="flex justify-end">
        <Button onClick={() => setOpenModal(true)}>
          <Plus className="size-4" aria-hidden="true" />
          Add provider
        </Button>
      </div>

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
                  <p className="text-sm text-muted">{provider.slug}</p>
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
                <IconButton
                  variant="ghost"
                  aria-label={`Delete ${provider.display_name}`}
                  onClick={() => deleteMutation.mutate(provider.id)}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </IconButton>
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
        open={openModal}
        onClose={() => setOpenModal(false)}
        title="Add OAuth provider"
      >
        <form onSubmit={handleCreateProvider} className="flex flex-col gap-4">
          <Input
            label="Provider slug"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="e.g., google, github"
            required
          />
          <Input
            label="Display name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g., Sign in with Google"
            required
          />
          <div className="flex flex-col gap-2">
            <Input
              label="Issuer URL"
              value={issuerUrl}
              onChange={(e) => setIssuerUrl(e.target.value)}
              placeholder="https://example.com"
              type="url"
              required
            />
            <div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleDiscoverIssuer}
                loading={discoverMutation.isPending}
              >
                Discover endpoints
              </Button>
            </div>
          </div>
          <Input
            label="Client ID"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
          />
          <Input
            label="Client secret"
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            required
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setOpenModal(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={createMutation.isPending}>
              Create provider
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
