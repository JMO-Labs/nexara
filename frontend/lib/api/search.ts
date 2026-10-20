/**
 * @file lib/api/search.ts
 * @brief Global search REST endpoint client.
 *
 * Backend returns results grouped by content type:
 *   { query, results: { posts: { items, total, next_cursor }, ... } }
 * The client flattens those into a single ranked-ish list so consumers
 * (command palette, search page) can render uniformly.
 */
import { apiGet } from "./client";

export type SearchType =
  | "posts"
  | "users"
  | "events"
  | "subgroups"
  | "comments";

export interface SearchResultItem {
  id: string;
  type: SearchType;
  title: string;
  snippet: string;
  created_at: string;
  parent_id?: string | null;
  slug?: string | null;
}

interface RawTypeResults {
  items: Omit<SearchResultItem, "type">[];
  total: number;
  next_cursor: string | null;
}

interface RawSearchResponse {
  query: string;
  results: Partial<Record<SearchType, RawTypeResults>>;
}

export interface SearchResponse {
  items: SearchResultItem[];
  next_cursor: string | null;
  has_more: boolean;
  totals: Partial<Record<SearchType, number>>;
}

interface SearchAllOptions {
  types?: string[];
  cursor?: string | null;
  limit?: number;
}

const SEARCH = "/api/v1/search";

export const searchAll = async (
  q: string,
  opts: SearchAllOptions = {},
): Promise<SearchResponse> => {
  const qs = new URLSearchParams({ q, limit: String(opts.limit ?? 20) });
  if (opts.types && opts.types.length > 0) {
    qs.set("types", opts.types.join(","));
  }
  if (opts.cursor) {
    qs.set("cursor", opts.cursor);
  }
  const raw = await apiGet<RawSearchResponse>(`${SEARCH}?${qs}`);

  const items: SearchResultItem[] = [];
  const totals: Partial<Record<SearchType, number>> = {};
  let nextCursor: string | null = null;
  let hasMore = false;

  for (const [key, bucket] of Object.entries(raw.results ?? {})) {
    if (!bucket) continue;
    const type = key as SearchType;
    totals[type] = bucket.total;
    for (const it of bucket.items) {
      items.push({ ...it, type });
    }
    if (bucket.next_cursor) {
      nextCursor = bucket.next_cursor;
      hasMore = true;
    }
  }

  return { items, next_cursor: nextCursor, has_more: hasMore, totals };
};
