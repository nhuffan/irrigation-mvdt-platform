/** Resolve record fragments after streamed technical records have mounted. */
export function observeRecordFragment(recordIds: readonly string[]): () => void {
  const targets = new Set(recordIds.map(id => `record-${id}`));
  const reveal = () => {
    const id = window.location.hash.slice(1);
    if (!targets.has(id)) return;
    const target = document.getElementById(id);
    if (!target) return;
    target.scrollIntoView({ block: "center" });
    target.focus({ preventScroll: true });
  };
  reveal();
  window.addEventListener("hashchange", reveal);
  return () => window.removeEventListener("hashchange", reveal);
}
