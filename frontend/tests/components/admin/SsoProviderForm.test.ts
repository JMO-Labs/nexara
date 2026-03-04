/**
 * @file tests/components/admin/SsoProviderForm.test.ts
 * @brief Tests for SsoProviderForm component.
 */
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { ref } from "vue";
import SsoProviderForm from "~/components/admin/SsoProviderForm.vue";

vi.mock("~/composables/useSsoProviderForm", () => ({
  useSsoProviderForm: () => ({
    form: ref({
      provider_type: "oidc",
      display_name: "",
      slug: "",
      icon_url: "",
      issuer_url: "",
      authorization_endpoint: "",
      token_endpoint: "",
      userinfo_endpoint: "",
      jwks_uri: "",
      end_session_endpoint: "",
      client_id: "",
      client_secret: "",
      group_mappings: {},
      default_role: "member",
      group_claim: "groups",
      scopes: "openid profile email groups",
      sub_claim: "sub",
      email_claim: "email",
      name_claim: "name",
      avatar_claim: "picture",
      auto_create_users: true,
      enabled: true,
    }),
    groupMappingsList: ref([]),
    saving: ref(false),
    maybeSlugFromDisplayName: vi.fn(),
    addGroupMapping: vi.fn(),
    removeGroupMapping: vi.fn(),
    discover: vi.fn(),
    save: vi.fn().mockResolvedValue(true),
  }),
}));

describe("SsoProviderForm", () => {
  it("renders form heading for add mode", () => {
    const wrapper = mount(SsoProviderForm);
    expect(wrapper.text()).toContain("admin.addProvider");
  });

  it("renders form heading for edit mode when provider prop is passed", () => {
    const wrapper = mount(SsoProviderForm, {
      props: {
        provider: {
          id: "p1",
          provider_type: "oidc",
          display_name: "Test IdP",
          slug: "test-idp",
          icon_url: null,
          issuer_url: null,
          authorization_endpoint: "",
          token_endpoint: "",
          userinfo_endpoint: null,
          jwks_uri: null,
          end_session_endpoint: null,
          client_id: "client",
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
        },
      },
    });
    expect(wrapper.text()).toContain("admin.editProvider");
  });

  it("renders required form fields", () => {
    const wrapper = mount(SsoProviderForm);

    expect(wrapper.find('input[type="text"]').exists()).toBe(true);
    const inputs = wrapper.findAll("input");
    const displayNameInput = inputs.find(
      (i) => i.attributes("placeholder") !== undefined || i.element.id === "",
    );
    expect(wrapper.text()).toContain("admin.displayName");
    expect(wrapper.text()).toContain("admin.clientId");
    expect(wrapper.find('input[type="password"]').exists()).toBe(true);
  });

  it("emits cancelled when cancel button clicked", async () => {
    const wrapper = mount(SsoProviderForm);
    const cancelBtn = wrapper
      .findAll("button")
      .find((b) => b.text().includes("common.cancel"));

    expect(cancelBtn).toBeDefined();
    await cancelBtn!.trigger("click");

    expect(wrapper.emitted("cancelled")).toBeTruthy();
    expect(wrapper.emitted("cancelled")).toHaveLength(1);
  });

  it("shows slug field", () => {
    const wrapper = mount(SsoProviderForm);
    expect(wrapper.text()).toContain("admin.slug");
  });
});
