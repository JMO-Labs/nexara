/**
 * @file theme/font.ts
 * @brief Outfit, the only typeface (weights 300/400/500/600).
 */
import { Outfit } from "next/font/google";

export const outfit = Outfit({
  weight: ["300", "400", "500", "600"],
  variable: "--font-outfit",
  display: "swap",
  subsets: ["latin"],
});
