"use client";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
export function RetryView() {
  const router = useRouter(); const [pending, startTransition] = useTransition();
  return <button className="button button-secondary" disabled={pending} aria-busy={pending} onClick={() => startTransition(() => router.refresh())}>{pending ? "Retrying…" : "Retry"}</button>;
}
