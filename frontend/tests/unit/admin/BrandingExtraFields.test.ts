/**
 * @file tests/unit/admin/BrandingExtraFields.test.ts
 * @brief Payload building for the extra branding fields.
 */
import { describe, expect, it } from "vitest";
import {
  extraChanges,
  type ExtraValues,
} from "@/components/admin/BrandingExtraFields";

const ID = "123e4567-e89b-12d3-a456-426614174000";
const init: ExtraValues = {
  email_logo_media_id: ID,
  email_footer_text: "",
  email_sender_name: "",
  landing_cta_text: "",
  landing_show_feature_list: true,
  pwa_icon_192_media_id: ID,
  pwa_icon_512_media_id: "",
};

describe("extraChanges", () => {
  it("drops cleared media IDs instead of sending empty strings", () => {
    const body = extraChanges(
      { ...init, email_logo_media_id: "", pwa_icon_192_media_id: "" },
      init,
    );
    expect(Object.values(body)).not.toContain("");
    expect(body).toEqual({});
  });

  it("keeps changed media IDs and text fields", () => {
    const other = "223e4567-e89b-12d3-a456-426614174000";
    const body = extraChanges(
      { ...init, pwa_icon_512_media_id: other, email_footer_text: "Bye" },
      init,
    );
    expect(body).toEqual({
      pwa_icon_512_media_id: other,
      email_footer_text: "Bye",
    });
  });
});
