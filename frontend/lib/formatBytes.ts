/**
 * @file lib/formatBytes.ts
 * @brief Human-readable byte size formatting (binary units).
 */
const UNITS = ["B", "KB", "MB", "GB", "TB"];

/**
 * @brief Format a byte count, e.g. 1536 -> "1.5 KB".
 * @param bytes Byte count; null/negative are treated as 0.
 * @return Formatted string.
 */
export function formatBytes(bytes: number | null | undefined): string {
  let size = bytes && bytes > 0 ? bytes : 0;
  let i = 0;
  while (size >= 1024 && i < UNITS.length - 1) {
    size /= 1024;
    i += 1;
  }
  return i === 0 ? `${size} B` : `${size.toFixed(1)} ${UNITS[i]}`;
}
