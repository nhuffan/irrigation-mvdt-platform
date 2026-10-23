"use client";
import { RESERVOIR_HREF } from "@/lib/site-scope";
import Link from "next/link";
import { usePathname } from "next/navigation";
export function AppHeader() {
  const pathname = usePathname();
  return (
    <header className="app-header">
      <div className="header-inner">
        <Link href="/" className="brand">
          <span className="brand-icon" aria-hidden="true">
            ≈
          </span>
          <span>
            Irrigation MVDT
            <span className="brand-subtitle">Reservoir portal</span>
          </span>
        </Link>
        <nav aria-label="Main navigation">
          {[
            [RESERVOIR_HREF, "Overview"],
            ["/map", "GIS Map"],
            ["/methodology", "Methodology & Evidence"],
            [`${RESERVOIR_HREF}/3d`, "3D"],
            ["/ai-research-preview", "AI Research"],
          ].map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
