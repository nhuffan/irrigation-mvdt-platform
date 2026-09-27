import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Irrigation MVDT Platform",
  description: "Development reservoir registry — FastAPI and PostGIS",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
