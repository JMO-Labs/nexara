/**
 * @file lib/api/listTemplates.ts
 * @brief List templates REST client (CRUD + clone into a list).
 */
import { apiDelete, apiGet, apiPost, apiPut, seg } from "./client";
import {
  camelize,
  snakeize,
  type List,
  type ListTemplate,
  type ListTemplateCloneInput,
  type ListTemplateInput,
  type ListTemplatePage,
} from "./listTypes";

const BASE = "/api/v1/list_templates";

const mapTemplate = (raw: unknown): ListTemplate => {
  const t = camelize<ListTemplate>(raw);
  return {
    ...t,
    fields: (t.fields ?? []).map((f) => camelize(f)),
    items: (t.items ?? []).map((i) => camelize(i)),
  };
};

const body = (d: Partial<ListTemplateInput>) => ({
  ...snakeize(d),
  ...(d.fields && { fields: d.fields.map(snakeize) }),
  ...(d.items && { items: d.items.map(snakeize) }),
});

export const templateApi = {
  async getTemplates(
    p: { cursor?: string; limit?: number } = {},
  ): Promise<ListTemplatePage> {
    const q = new URLSearchParams();
    if (p.cursor) q.set("cursor", p.cursor);
    if (p.limit !== undefined) q.set("limit", String(p.limit));
    const s = q.toString();
    const r = await apiGet<{
      templates: unknown[];
      cursor?: string | null;
      has_more?: boolean;
    }>(`${BASE}${s ? `?${s}` : ""}`);
    return {
      templates: r.templates.map(mapTemplate),
      nextCursor: r.has_more && r.cursor ? r.cursor : undefined,
    };
  },
  async getTemplate(id: string): Promise<ListTemplate> {
    return mapTemplate(await apiGet(`${BASE}/${seg(id)}`));
  },
  async createTemplate(data: ListTemplateInput): Promise<ListTemplate> {
    return mapTemplate(await apiPost(BASE, body(data)));
  },
  async updateTemplate(
    id: string,
    data: Partial<ListTemplateInput>,
  ): Promise<ListTemplate> {
    return mapTemplate(await apiPut(`${BASE}/${seg(id)}`, body(data)));
  },
  deleteTemplate(id: string): Promise<void> {
    return apiDelete(`${BASE}/${seg(id)}`);
  },
  async cloneTemplate(
    id: string,
    data: ListTemplateCloneInput = {},
  ): Promise<List> {
    return camelize(await apiPost(`${BASE}/${seg(id)}/clone`, snakeize(data)));
  },
};
