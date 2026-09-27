"use client";
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
            ["/", "Registry"],
            ["/map", "GIS Map"],
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
