import type { Metadata, Viewport } from 'next';
import './fonts.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Flip Flop HQ — Tu trading, en otra órbita',
  description:
    'Conoce Flip Flop HQ: automatización, seguimiento y agenda de trading en una app para móvil y desktop. Explora la demo y descubre el modelo.',
  icons: {
    icon: [{ url: '/flipflop-hq-mark-v4.png', type: 'image/png' }],
    apple: [{ url: '/flipflop-hq-mark-v4.png', type: 'image/png' }],
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#000000',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
