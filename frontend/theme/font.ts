/**
 * @file theme/font.ts
 * @brief Hanken Grotesk, the only typeface (weights 400/600/900).
 */
import { Hanken_Grotesk } from "next/font/google";

export const hanken = Hanken_Grotesk({
  weight: ["400", "600", "900"],
  variable: "--font-hanken",
  display: "swap",
  subsets: ["latin"],
});
