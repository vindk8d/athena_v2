import '../globals.css';
import type { ReactNode } from 'react';
import { Toaster } from '@/components/ui/toaster';

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
