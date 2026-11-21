import type { Metadata } from "next";
import localFont from "next/font/local";
import { AppHeader } from "@/components/app-header";
import { SYNTHETIC_DEMO } from "@/lib/site-scope";
import "./globals.css";
const inter = localFont({
  src: "./fonts/InterVariable.woff2",
  variable: "--font-inter",
  weight: "100 900",
  style: "normal",
  display: "swap",
  fallback: ["Arial", "sans-serif"],
});

export const metadata: Metadata = {
  title: "Irrigation MVDT · Reservoir Portal",
  description: "Reservoir asset management, GIS and 3D workspace",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        {SYNTHETIC_DEMO && <p role="note" className="demo-banner">Public demo · Synthetic data written for this project, not research evidence. Real reservoir data stays private.</p>}
        <AppHeader />
        {children}
        <footer className="site-footer">
          Source-reported information and reference locations retain their stated evidence limitations.
        </footer>
      </body>
    </html>
  );
}
