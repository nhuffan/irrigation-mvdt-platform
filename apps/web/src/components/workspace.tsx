"use client";
import { useEffect, useReducer, useRef, type ReactNode } from "react";
import { workspaceLayout } from "@/lib/workspace-layout";
export function Workspace({ title, children, panel, tools }: { title: string; children: ReactNode; panel: ReactNode; tools?: ReactNode }) {
  const [layout, dispatch] = useReducer(workspaceLayout, { expanded: false, panelOpen: true });
  const root = useRef<HTMLElement>(null);
  const expandButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!layout.expanded) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { dispatch("escape"); expandButton.current?.focus(); }
      if (event.key === "Tab" && root.current) {
        const controls = [...root.current.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, select, summary, [tabindex="0"]')].filter(el => el.getClientRects().length > 0);
        const first = controls[0], last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    window.addEventListener("keydown", escape);
    return () => { document.body.style.overflow = previous; window.removeEventListener("keydown", escape); };
  }, [layout.expanded]);
  return <section ref={root} className={`canvas-workspace${layout.expanded ? " is-expanded" : ""}${layout.panelOpen ? "" : " panel-closed"}`} aria-label={`${title} workspace`}>
    <div className="workspace-toolbar">
      <strong>{title}</strong>
      <button type="button" onClick={() => dispatch("panel")} aria-expanded={layout.panelOpen}>{layout.panelOpen ? "Hide panel" : "Show panel"}</button>
      <button type="button" ref={expandButton} onClick={() => dispatch("expand")} aria-pressed={layout.expanded}>{layout.expanded ? "Exit expanded view" : `Expand ${title}`}</button>
      {layout.expanded && <span className="muted">Escape to exit</span>}
    </div>
    {tools}
    <div className="workspace-grid">
      <div className="workspace-canvas">{children}</div>
      <div className="workspace-inspector" hidden={!layout.panelOpen}>{panel}</div>
    </div>
  </section>;
}
