"use client";
/**
 * @file theme/EmotionRegistry.tsx
 * @brief SSR-safe Emotion cache for App Router. Flushes inserted styles
 *        into the streaming HTML so first paint matches client.
 *        Style payload is library-generated CSS (Emotion), never user input.
 */
import { useState } from "react";
import { useServerInsertedHTML } from "next/navigation";
import createCache, { type EmotionCache, type Options } from "@emotion/cache";
import { CacheProvider } from "@emotion/react";

export default function EmotionRegistry({
  children,
  options = { key: "nx-joy", prepend: true },
}: {
  children: React.ReactNode;
  options?: Options;
}) {
  const [{ cache, flush }] = useState(() => {
    const c: EmotionCache = createCache(options);
    c.compat = true;
    const prevInsert = c.insert;
    let inserted: string[] = [];
    c.insert = (...args) => {
      const serialized = args[1];
      if (c.inserted[serialized.name] === undefined)
        inserted.push(serialized.name);
      return prevInsert(...args);
    };
    const f = () => {
      const prev = inserted;
      inserted = [];
      return prev;
    };
    return { cache: c, flush: f };
  });

  useServerInsertedHTML(() => {
    const names = flush();
    if (names.length === 0) return null;
    let styles = "";
    for (const name of names) styles += cache.inserted[name];
    return (
      <style
        data-emotion={`${cache.key} ${names.join(" ")}`}
        suppressHydrationWarning
        dangerouslySetInnerHTML={{ __html: styles }}
      />
    );
  });

  return <CacheProvider value={cache}>{children}</CacheProvider>;
}
