/**
 * @file tests/composables/useSsoProviderForm.test.ts
 * @brief Tests for useSsoProviderForm composable.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { ref, nextTick } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { useSsoProviderForm } from "~/composables/useSsoProviderForm";
import type { OAuthProviderResponse } from "~/types/api";

const mockPost = vi.fn().mockResolvedValue({});
const mockPut = vi.fn().mockResolvedValue({});

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: vi.fn().mockResolvedValue({}),
    post: mockPost,
    put: mockPut,
    del: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock("~/stores/ui", () => ({
  useUiStore: () => ({
    showToast: vi.fn(),
  }),
}));

describe("useSsoProviderForm", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("initializes with default form state when provider is null", () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { form } = useSsoProviderForm(providerRef);

    expect(form.value.provider_type).toBe("oidc");
    expect(form.value.display_name).toBe("");
    expect(form.value.slug).toBe("");
    expect(form.value.client_id).toBe("");
  });

  it("populates form from provider when ref changes to non-null", async () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { form } = useSsoProviderForm(providerRef);

    const provider: OAuthProviderResponse = {
      id: "p1",
      provider_type: "oidc",
      display_name: "My IdP",
      slug: "my-idp",
      icon_url: null,
      issuer_url: "https://idp.example.com",
      authorization_endpoint: "https://idp.example.com/auth",
      token_endpoint: "https://idp.example.com/token",
      userinfo_endpoint: "https://idp.example.com/userinfo",
      jwks_uri: null,
      end_session_endpoint: null,
      client_id: "client-123",
      group_mappings: { admins: "admin" },
      default_role: "member",
      group_claim: "groups",
      scopes: "openid profile",
      sub_claim: "sub",
      email_claim: "email",
      name_claim: "name",
      avatar_claim: "picture",
      auto_create_users: true,
      enabled: true,
    };

    providerRef.value = provider;
    await nextTick();

    expect(form.value.display_name).toBe("My IdP");
    expect(form.value.slug).toBe("my-idp");
    expect(form.value.client_id).toBe("client-123");
    expect(form.value.issuer_url).toBe("https://idp.example.com");
  });

  it("maybeSlugFromDisplayName generates slug from display name", () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { form, maybeSlugFromDisplayName } = useSsoProviderForm(providerRef);

    form.value.display_name = "My OAuth Provider";
    maybeSlugFromDisplayName();

    expect(form.value.slug).toBe("my-oauth-provider");
  });

  it("addGroupMapping adds entry to groupMappingsList", () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { groupMappingsList, addGroupMapping } = useSsoProviderForm(
      providerRef,
    );

    expect(groupMappingsList.value).toHaveLength(0);

    addGroupMapping();
    expect(groupMappingsList.value).toHaveLength(1);
    expect(groupMappingsList.value[0]).toEqual({
      idp_group: "",
      role: "member",
    });

    addGroupMapping();
    expect(groupMappingsList.value).toHaveLength(2);
  });

  it("removeGroupMapping removes entry from groupMappingsList", () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { groupMappingsList, addGroupMapping, removeGroupMapping } =
      useSsoProviderForm(providerRef);

    addGroupMapping();
    addGroupMapping();
    addGroupMapping();
    expect(groupMappingsList.value).toHaveLength(3);

    removeGroupMapping(1);
    expect(groupMappingsList.value).toHaveLength(2);
  });

  it("save calls api.post for new provider and api.put for existing", async () => {
    const providerRef = ref<OAuthProviderResponse | null>(null);
    const { form, save } = useSsoProviderForm(providerRef);

    form.value.display_name = "New Provider";
    form.value.slug = "new-provider";
    form.value.client_id = "client-x";

    await save();
    expect(mockPost).toHaveBeenCalledWith(
      "/admin/oauth/providers",
      expect.objectContaining({
        display_name: "New Provider",
        slug: "new-provider",
        client_id: "client-x",
      }),
    );
    expect(mockPut).not.toHaveBeenCalled();

    vi.clearAllMocks();

    const existingProvider: OAuthProviderResponse = {
      id: "existing-1",
      provider_type: "oidc",
      display_name: "Existing",
      slug: "existing",
      icon_url: null,
      issuer_url: null,
      authorization_endpoint: "",
      token_endpoint: "",
      userinfo_endpoint: null,
      jwks_uri: null,
      end_session_endpoint: null,
      client_id: "client-y",
      group_mappings: {},
      default_role: "member",
      group_claim: "groups",
      scopes: "openid",
      sub_claim: "sub",
      email_claim: "email",
      name_claim: "name",
      avatar_claim: "picture",
      auto_create_users: true,
      enabled: true,
    };

    const editRef = ref<OAuthProviderResponse | null>(existingProvider);
    const { form: editForm, save: saveEdit } = useSsoProviderForm(editRef);

    editForm.value.display_name = "Updated Name";
    await saveEdit();

    expect(mockPut).toHaveBeenCalledWith(
      "/admin/oauth/providers/existing-1",
      expect.objectContaining({ display_name: "Updated Name" }),
    );
    expect(mockPost).not.toHaveBeenCalled();
  });
});
