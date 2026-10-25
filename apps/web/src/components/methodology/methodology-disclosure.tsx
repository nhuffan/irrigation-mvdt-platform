"use client";

import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";

const subscribeHash = (notify: () => void) => {
  window.addEventListener("hashchange", notify);
  return () => window.removeEventListener("hashchange", notify);
};
const hashSnapshot = () => window.location.hash;
const serverHash = () => "";
const retainedAnchors = new Set(["scope", "coverage", "process", "evaluation", "protocol", "reproducibility", "quality-results-basis", "source-age-basis"]);
export function methodologyAnchorTarget(hash: string): "workflow" | "retained" | null {
  let anchor: string;
  try { anchor = decodeURIComponent(hash.replace(/^#/, "")); } catch { return null; }
  if (/^research-(scope|data|functional|evaluation|results)$/.test(anchor)) return "workflow";
  return retainedAnchors.has(anchor) || /^methodology-asset-[A-Za-z0-9-]+$/.test(anchor) ? "retained" : null;
}

/** Keep research tools secondary, while old coverage and workflow links still work. */
export function MethodologyDisclosure({ children, title, retained = false }: { children: ReactNode; title: string; retained?: boolean }) {
  const hash = useSyncExternalStore(subscribeHash, hashSnapshot, serverHash);
  const [manual, setManual] = useState<{ hash: string; open: boolean } | null>(null);
  const target = methodologyAnchorTarget(hash);
  const active = retained ? target === "retained" : target !== null;
  const open = manual?.hash === hash ? manual.open : active;
  useEffect(() => {
    if (!open || !active) return;
    const frame = requestAnimationFrame(() => {
      if (window.location.hash !== hash) return;
      try { document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView({ block: "start" }); } catch { /* Invalid fragments stay harmless. */ }
    });
    return () => cancelAnimationFrame(frame);
  }, [active, hash, open]);
  return <details className="panel-disclosure" open={open} onToggle={event => setManual({hash, open: event.currentTarget.open})}>
    <summary>{title}</summary><div className="panel-section-body">{children}</div>
  </details>;
}
