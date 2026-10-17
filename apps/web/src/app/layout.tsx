import type { Metadata } from "next";
import { AppHeader } from "@/components/app-header";
import "./globals.css";
export const metadata: Metadata = {
  title: "Irrigation MVDT · Reservoir Portal",
  description: "Reservoir asset management, GIS and 3D workspace",
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
          Source-reported information and reference locations retain their stated evidence limitations.
        </footer>
      </body>
    </html>
  );
}
