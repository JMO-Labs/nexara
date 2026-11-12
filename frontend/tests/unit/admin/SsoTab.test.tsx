/**
 * @file tests/unit/admin/SsoTab.test.tsx
 * @brief SsoTab: list, SSO-only toggle/warning, add/edit/delete, test connection.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as oauth from "@/hooks/useAdminOauth";
import { SsoTab } from "@/components/admin/SsoTab";

vi.mock("@/hooks/useAdminOauth");
const confirmFn = vi.fn();
vi.mock("@/stores/confirmDialog", () => ({
  useConfirmDialog: (sel: (s: unknown) => unknown) =>
    sel({ confirm: confirmFn }),
}));

const provider = (over = {}) => ({
  id: "p1",
  slug: "kc",
  display_name: "Keycloak",
  provider_type: "oidc",
  issuer: "https://kc.example.com",
  client_id: "cid",
  scopes: "openid profile email",
  enabled: true,
  ...over,
});

const create = vi.fn();
const update = vi.fn();
const del = vi.fn();
const toggle = vi.fn();
const setSso = vi.fn();
const discover = vi.fn();

function setup(providers: unknown[], ssoOnly = false) {
  const m = (fn: unknown) => ({
    mutate: fn,
    mutateAsync: fn,
    isPending: false,
  });
  vi.mocked(oauth.useOauthProviders).mockReturnValue({
    data: providers,
    isLoading: false,
    error: null,
  } as never);
  vi.mocked(oauth.useSsoOnly).mockReturnValue({ data: ssoOnly } as never);
  vi.mocked(oauth.useSetSsoOnly).mockReturnValue(m(setSso) as never);
  vi.mocked(oauth.useCreateOauthProvider).mockReturnValue(m(create) as never);
  vi.mocked(oauth.useUpdateOauthProvider).mockReturnValue(m(update) as never);
  vi.mocked(oauth.useDeleteOauthProvider).mockReturnValue(m(del) as never);
  vi.mocked(oauth.useToggleOauthProvider).mockReturnValue(m(toggle) as never);
  vi.mocked(oauth.useDiscoverIssuer).mockReturnValue(m(discover) as never);
  render(<SsoTab />);
}

describe("SsoTab", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists providers with discovery url", () => {
    setup([provider()]);
    expect(screen.getByText("Keycloak")).toBeTruthy();
    expect(screen.getByText("https://kc.example.com")).toBeTruthy();
  });

  it("toggles SSO-only and shows subtitle when on", async () => {
    setup([provider()], true);
    expect(
      screen.getByText("Require all users to log in via SSO"),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole("switch", { name: "SSO only" }));
    expect(setSso).toHaveBeenCalledWith(false);
  });

  it("warns when SSO-only is on and no provider is enabled", () => {
    setup([provider({ enabled: false })], true);
    expect(screen.getByRole("alert").textContent).toMatch(
      /no providers are active/i,
    );
  });

  it("no warning when a provider is enabled", () => {
    setup([provider()], true);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("rejects non-HTTPS discovery url", async () => {
    setup([]);
    await userEvent.click(screen.getByRole("button", { name: /add oidc/i }));
    const dlg = screen.getByRole("dialog");
    await userEvent.type(within(dlg).getByLabelText("Provider name"), "okta");
    await userEvent.type(
      within(dlg).getByLabelText("Discovery URL"),
      "http://x.example.com",
    );
    await userEvent.type(within(dlg).getByLabelText("Client ID"), "a");
    await userEvent.type(within(dlg).getByLabelText("Client secret"), "b");
    await userEvent.click(
      within(dlg).getByRole("button", { name: "Create provider" }),
    );
    expect(within(dlg).getByText(/must use https/i)).toBeTruthy();
    expect(create).not.toHaveBeenCalled();
  });

  it("creates a provider with default scopes", async () => {
    setup([]);
    await userEvent.click(screen.getByRole("button", { name: /add oidc/i }));
    const dlg = screen.getByRole("dialog");
    await userEvent.type(within(dlg).getByLabelText("Provider name"), "okta");
    await userEvent.type(
      within(dlg).getByLabelText("Discovery URL"),
      "https://o.example.com",
    );
    await userEvent.type(within(dlg).getByLabelText("Client ID"), "a");
    await userEvent.type(within(dlg).getByLabelText("Client secret"), "b");
    await userEvent.click(
      within(dlg).getByRole("button", { name: "Create provider" }),
    );
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({
        slug: "okta",
        issuer: "https://o.example.com",
        client_id: "a",
        client_secret: "b",
        scopes: "openid profile email",
      }),
    );
  });

  it("test connection calls discovery", async () => {
    discover.mockResolvedValue({});
    setup([]);
    await userEvent.click(screen.getByRole("button", { name: /add oidc/i }));
    const dlg = screen.getByRole("dialog");
    await userEvent.type(
      within(dlg).getByLabelText("Discovery URL"),
      "https://o.example.com",
    );
    await userEvent.click(
      within(dlg).getByRole("button", { name: "Test connection" }),
    );
    await waitFor(() =>
      expect(discover).toHaveBeenCalledWith("https://o.example.com"),
    );
    expect(await within(dlg).findByText(/connection ok/i)).toBeTruthy();
  });

  it("edit omits secret unless checkbox ticked", async () => {
    setup([provider()]);
    await userEvent.click(
      screen.getByRole("button", { name: "Edit Keycloak" }),
    );
    const dlg = screen.getByRole("dialog");
    expect(within(dlg).queryByLabelText("Client secret")).toBeNull();
    expect(
      (within(dlg).getByLabelText("Client ID") as HTMLInputElement).value,
    ).toBe("cid");
    await userEvent.click(
      within(dlg).getByRole("button", { name: "Save changes" }),
    );
    expect(update).toHaveBeenCalledTimes(1);
    const arg = update.mock.calls[0][0];
    expect(arg.providerId).toBe("p1");
    expect(arg.updates).not.toHaveProperty("client_secret");
  });

  it("edit sends secret when 'Update client secret' ticked", async () => {
    setup([provider()]);
    await userEvent.click(
      screen.getByRole("button", { name: "Edit Keycloak" }),
    );
    const dlg = screen.getByRole("dialog");
    await userEvent.click(
      within(dlg).getByRole("checkbox", { name: /update client secret/i }),
    );
    await userEvent.type(within(dlg).getByLabelText("Client secret"), "new");
    await userEvent.click(
      within(dlg).getByRole("button", { name: "Save changes" }),
    );
    expect(update.mock.calls[0][0].updates.client_secret).toBe("new");
  });

  it("delete requires confirmation", async () => {
    confirmFn.mockResolvedValue(true);
    setup([provider()]);
    await userEvent.click(
      screen.getByRole("button", { name: "Delete Keycloak" }),
    );
    await waitFor(() => expect(del).toHaveBeenCalledWith("p1"));
    expect(confirmFn.mock.calls[0][0].message).toMatch(
      /won't be able to log in/i,
    );
  });

  it("delete cancelled does nothing", async () => {
    confirmFn.mockResolvedValue(false);
    setup([provider()]);
    await userEvent.click(
      screen.getByRole("button", { name: "Delete Keycloak" }),
    );
    await waitFor(() => expect(confirmFn).toHaveBeenCalled());
    expect(del).not.toHaveBeenCalled();
  });
});
