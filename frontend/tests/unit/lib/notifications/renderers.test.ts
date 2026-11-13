/**
 * @file tests/unit/lib/notifications/renderers.test.ts
 * @brief Default + custom notification renderers.
 */
import { describe, it, expect, beforeEach } from "vitest";
import {
  _interpolate,
  registerRenderer,
  renderNotif,
  _resetRenderers,
} from "@/lib/notifications/renderers";
import type { NotificationTypeDescriptor } from "@/lib/notifications/types";

const t = (k: string) => `T:${k}`;

const type: NotificationTypeDescriptor = {
  key: "event.invite",
  category: "event",
  default_channels: {
    inapp: true,
    email: false,
    push: false,
    webhook: false,
    toast: false,
  },
  user_configurable: [],
  group_window_seconds: null,
  toast_on_arrival: false,
  bypass_dnd: false,
  digestable: false,
  actions: [
    {
      key: "accept",
      label_i18n: "notif.accept",
      method: "POST",
      url_template: "/api/v1/events/{target_id}/rsvp?by={actor_id}",
      style: "primary",
    },
  ],
  label_i18n: "notif.event.invite",
  icon: "calendar",
  plugin_id: null,
  payload_schema: {},
};

describe("_interpolate", () => {
  it("replaces known keys and leaves unknown placeholders", () => {
    expect(_interpolate("/a/{x}/{y}", { x: 1 })).toBe("/a/1/{y}");
  });
});

describe("renderNotif default", () => {
  beforeEach(() => _resetRenderers());

  it("maps title, body, icon, link", () => {
    const r = renderNotif(type, { message: "hi", link: "/e/1" }, t);
    expect(r).toMatchObject({
      title: "T:notif.event.invite",
      body: "hi",
      icon: "calendar",
      link: "/e/1",
    });
  });

  it("falls back to null link and empty body", () => {
    const r = renderNotif(type, {}, t);
    expect(r.link).toBeNull();
    expect(r.body).toBe("");
  });

  it("maps actions with url templating", () => {
    const r = renderNotif(type, { target_id: "e1", actor_id: "u2" }, t);
    expect(r.actions).toEqual([
      {
        key: "accept",
        label: "T:notif.accept",
        method: "POST",
        url: "/api/v1/events/e1/rsvp?by=u2",
        style: "primary",
      },
    ]);
  });
});

describe("registerRenderer", () => {
  beforeEach(() => _resetRenderers());

  it("uses custom renderer for its type only", () => {
    registerRenderer("event.invite", () => ({
      title: "custom",
      body: "",
      icon: "x",
      link: null,
      actions: [],
    }));
    expect(renderNotif(type, {}, t).title).toBe("custom");
    expect(renderNotif({ ...type, key: "other" }, {}, t).title).toBe(
      "T:notif.event.invite",
    );
  });
});
