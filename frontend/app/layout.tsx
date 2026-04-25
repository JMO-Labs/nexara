/**
 * @file app/layout.tsx
 * @brief Root layout. Mounts fonts, providers, and the no-flash color-scheme
 *        bootstrap script so dark/light mode hydrates without flicker.
 */
import type { Metadata, Viewport } from 'next';
import InitColorSchemeScript from '@mui/joy/InitColorSchemeScript';
import { fraunces, geist, geistMono } from '@/theme/fonts';
import ServiceWorkerRegistrar from '@/components/layout/ServiceWorkerRegistrar';
import Providers from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: { default: 'Nexara', template: '%s · Nexara' },
  description: 'A warm, self-hosted home for the communities you love.',
  applicationName: 'Nexara',
  manifest: '/manifest.webmanifest',
  appleWebApp: { capable: true, title: 'Nexara', statusBarStyle: 'default' },
  formatDetection: { telephone: false, email: false, address: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F5EFE6' },
    { media: '(prefers-color-scheme: dark)', color: '#1A1816' },
  ],
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fraunces.variable} ${geist.variable} ${geistMono.variable}`}
    >
      <body>
        <InitColorSchemeScript defaultMode="system" />
        <Providers>{children}</Providers>
        <ServiceWorkerRegistrar />
      </body>
    </html>
  );
}
