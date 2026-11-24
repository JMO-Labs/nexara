/**
 * @file tests/unit/admin/sso/SsoProviderForm.test.tsx
 * @brief SSO wizard: presets prefill discovery, rules and mappings reach the payload.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as oauth from "@/hooks/useAdminOauth";
import * as subgroups from "@/hooks/useSubgroups";
import { SsoProviderForm } from "@/components/admin/SsoProviderForm";
import type { OAuthProviderResponse } from "@/lib/api/adminOauth";
import { GROUPS, PRESETS } from "./fixtures";

vi.mock("@/hooks/useAdminOauth");
vi.mock("@/hooks/useSubgroups");

const onSubmit = vi.fn();

function setup(provider: Partial<OAuthProviderResponse> | null = null) {
  vi.mocked(oauth.useOauthPresets).mockReturnValue({
    data: PRESETS,
  } as never);
  vi.mocked(oauth.useCallbackTemplate).mockReturnValue({
    data: { template: "https://home.example/api/v1/oauth/{slug}/callback" },
  } as never);
  vi.mocked(subgroups.useSubgroupList).mockReturnValue({
    data: GROUPS,
  } as never);
  render(
    <SsoProviderForm
      provider={provider as OAuthProviderResponse | null}
      pending={false}
      onCancel={vi.fn()}
      onSubmit={onSubmit}
      onTest={vi.fn()}
    />,
  );
}

const next = () =>
  userEvent.click(screen.getByRole("button", { name: "Next" }));

async function fillAuthentik() {
  await userEvent.click(screen.getByRole("radio", { name: /authentik/i }));
  await next();
  await userEvent.type(screen.getByLabelText("Host"), "auth.example.com");
  await userEvent.type(screen.getByLabelText("Application slug"), "nexara");
  await userEvent.type(screen.getByLabelText("Client ID"), "cid");
  await userEvent.type(screen.getByLabelText("Client secret"), "sec");
}

describe("SsoProviderForm wizard", () => {
  beforeEach(() => vi.clearAllMocks());

  it("picking authentik prefills the discovery template from host/slug", async () => {
    setup();
    await fillAuthentik();
    expect(
      screen.getByText(
        "https://auth.example.com/application/o/nexara/.well-known/openid-configuration",
      ),
    ).toBeTruthy();
    expect((screen.getByLabelText("Scopes") as HTMLInputElement).value).toBe(
      "openid email profile",
    );
    expect(screen.getByText(/oauth\/authentik\/callback/)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: "Create provider" }),
    );
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        preset: "authentik",
        provider_type: "oidc",
        slug: "authentik",
        discovery_url:
          "https://auth.example.com/application/o/nexara/.well-known/openid-configuration",
        claim_mapping: { groups: "groups", group_mapping: {} },
      }),
      true,
    );
  });

  it("moves focus to the step heading on step change", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: /authentik/i }));
    await next();
    const h = screen.getByRole("heading", { name: /step 2 of 5: connection/i });
    expect(document.activeElement).toBe(h);
    expect(
      screen
        .getByRole("button", { name: "2. Connection" })
        .getAttribute("aria-current"),
    ).toBe("step");
  });

  it("requires https discovery before leaving connection", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: /custom oidc/i }));
    await next();
    await userEvent.type(screen.getByLabelText("Discovery URL"), "http://x.io");
    await next();
    expect(screen.getByText(/must use https/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /connection/i })).toBeTruthy();
  });

  it("oauth2 preset sends fixed endpoints and no discovery url", async () => {
    setup();
    await userEvent.click(screen.getByRole("radio", { name: /github/i }));
    await next();
    expect(
      screen.queryByRole("button", { name: "Test connection" }),
    ).toBeNull();
    await userEvent.type(screen.getByLabelText("Client ID"), "cid");
    await userEvent.type(screen.getByLabelText("Client secret"), "sec");
    await userEvent.click(
      screen.getByRole("button", { name: "Create provider" }),
    );
    const v = onSubmit.mock.calls[0][0];
    expect(v.provider_type).toBe("oauth2");
    expect(v.token_endpoint).toBe(
      "https://github.com/login/oauth/access_token",
    );
    expect(v).not.toHaveProperty("discovery_url");
  });

  it("rules and a mapping row save to claim_mapping.group_mapping", async () => {
    setup();
    await fillAuthentik();
    await next(); // rules
    await userEvent.click(
      screen.getByRole("switch", { name: "Create accounts automatically" }),
    );
    await userEvent.type(
      screen.getByLabelText("Add domain"),
      "@Smith.Family{Enter}",
    );
    await userEvent.type(screen.getByLabelText("Required group"), "nexara");
    await next(); // mappings
    await userEvent.click(screen.getByRole("button", { name: /add mapping/i }));
    await userEvent.type(screen.getByLabelText("Provider group"), "smiths");
    await userEvent.selectOptions(screen.getByLabelText("Role"), "admin");
    const row = screen.getByRole("group", { name: "Mapping for smiths" });
    await userEvent.click(
      within(row).getByRole("checkbox", { name: "Smith Family" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create provider" }),
    );
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      auto_create_users: false,
      allowed_domains: ["smith.family"],
      required_group: "nexara",
      claim_mapping: {
        groups: "groups",
        group_mapping: {
          smiths: [
            { subgroup_id: null, role: "admin" },
            { subgroup_id: "g-smith", role: "member" },
          ],
        },
      },
    });
  });

  it("edit keeps secret write-only and loads saved mappings", async () => {
    setup({
      id: "p1",
      slug: "kc",
      display_name: "Keycloak",
      provider_type: "oidc",
      preset: "custom",
      issuer: "https://kc.example.com",
      discovery_url: "https://kc.example.com/.well-known/openid-configuration",
      client_id: "cid",
      scopes: "openid",
      allowed_domains: [],
      default_role: "member",
      auto_create_users: true,
      sync_profile: true,
      required_group: null,
      callback_url: "https://home.example/api/v1/oauth/kc/callback",
      claim_mapping: {
        group_mapping: { ops: { subgroup_id: "g-club", role: "member" } },
      },
    });
    const secret = screen.getByLabelText("Client secret") as HTMLInputElement;
    expect(secret.value).toBe("");
    expect(secret.placeholder).toBe("Leave blank to keep current");
    expect(
      screen.getByText("https://home.example/api/v1/oauth/kc/callback"),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "4. Mappings" }));
    const row = screen.getByRole("group", { name: "Mapping for ops" });
    expect(
      (
        within(row).getByRole("checkbox", {
          name: "Book Club",
        }) as HTMLInputElement
      ).checked,
    ).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    const [v, secretChanged] = onSubmit.mock.calls[0];
    expect(secretChanged).toBe(false);
    expect(v).not.toHaveProperty("discovery_url"); // unchanged: no re-discovery
    expect(v.claim_mapping.group_mapping).toEqual({
      ops: { subgroup_id: "g-club", role: "member" }, // stored shape kept
    });
  });
});
