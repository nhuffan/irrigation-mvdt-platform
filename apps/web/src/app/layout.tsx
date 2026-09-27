import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import "./globals.css";
export const metadata: Metadata = {
  title: "Irrigation MVDT · Reservoir Portal",
  description: "Reservoir registry and GIS explorer",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppHeader />
        {children}
        <footer className="site-footer">
          Development dataset · Coordinates and readiness levels are
          illustrative, not verified research data.
        </footer>
      </body>
    </html>
  );
}
