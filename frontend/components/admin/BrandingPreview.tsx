/**
 * @file components/admin/BrandingPreview.tsx
 * @brief Live preview of the palette on light and dark surfaces.
 */
import type { ColorKey } from "@/lib/branding-palette";

/**
 * @brief Sample content on both surfaces.
 * @param props colors and fonts
 * @return preview panel
 */
export function BrandingPreview({
  colors,
  font,
  mono,
}: {
  colors: Record<ColorKey, string>;
  font: string;
  mono: string;
}) {
  const pane = (mode: "light" | "dark") => {
    const bg = colors[`color_surface_${mode}`];
    const fg = colors[`color_text_${mode}`];
    const pr =
      mode === "light" ? colors.color_primary : colors.color_primary_dark;
    return (
      <div
        data-testid={`branding-preview-${mode}`}
        style={{
          backgroundColor: bg,
          color: fg,
          fontFamily: `${font}, system-ui, sans-serif`,
        }}
        className="flex flex-col gap-2 rounded-xl border p-4"
      >
        <h3 style={{ color: pr }} className="text-lg font-bold">
          Welcome to the community
        </h3>
        <p className="text-sm">Sample body text on the {mode} surface.</p>
        <code style={{ fontFamily: `${mono}, monospace` }} className="text-xs">
          const hello = &quot;world&quot;;
        </code>
        <span
          style={{ backgroundColor: colors.color_accent, color: "#14301E" }}
          className="w-fit rounded-full px-3 py-1 text-sm font-medium"
        >
          Accent badge
        </span>
      </div>
    );
  };
  return (
    <section aria-label="Live preview" className="grid gap-3 sm:grid-cols-2">
      {pane("light")}
      {pane("dark")}
    </section>
  );
}
