"use client";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
export function SectionError({ title }: { title: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <section className="panel mt-6" role="alert">
      <h2>{title}</h2>
      <p className="muted mt-3">
        Unable to load {title.toLowerCase()}. This does not mean no records
        exist.
      </p>
      <button
        className="locate-button mt-4"
        disabled={pending}
        onClick={() => startTransition(() => router.refresh())}
      >
        {pending ? "Retrying…" : "Retry"}
      </button>
    </section>
  );
}
