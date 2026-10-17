export type WorkspaceLayout = { expanded: boolean; panelOpen: boolean };
export function workspaceLayout(state: WorkspaceLayout, action: "expand" | "panel" | "escape"): WorkspaceLayout {
  if (action === "escape") return { ...state, expanded: false };
  return action === "expand" ? { ...state, expanded: !state.expanded } : { ...state, panelOpen: !state.panelOpen };
}
// Observe actual container changes rather than rebuilding map/model instances.
export function observeCanvasResize(element: Element, resize: () => void) {
  let frame = 0;
  const observer = new ResizeObserver(() => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(resize);
  });
  observer.observe(element);
  return () => { observer.disconnect(); cancelAnimationFrame(frame); };
}
