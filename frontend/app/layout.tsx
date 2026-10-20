/**
 * @file app/layout.tsx
 * @brief Root layout. Mounts font and providers. next-themes sets the `dark`
 *        class on <html> before paint (no scheme flash).
 */
import type { Metadata, Viewport } from "next";
import { hanken } from "@/theme/font";
import ServiceWorkerRegistrar from "@/components/layout/ServiceWorkerRegistrar";
import Providers from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Nexara", template: "%s · Nexara" },
  description: "A private home for your family and friends.",
  applicationName: "Nexara",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: "Nexara", statusBarStyle: "default" },
  formatDetection: { telephone: false, email: false, address: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#E9F1E4" },
    { media: "(prefers-color-scheme: dark)", color: "#0E1F15" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={hanken.variable}>
      <body>
        <Providers>{children}</Providers>
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
