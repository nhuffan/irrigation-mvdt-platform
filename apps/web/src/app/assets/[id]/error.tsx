"use client";
export default function AssetError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="page-shell">
      <section className="panel" role="alert">
        <p className="eyebrow">Connection issue</p>
        <h1>Asset data is unavailable</h1>
        <p className="muted my-5">
          We could not load the latest asset information. Please try again
          shortly.
        </p>
        <button className="button" onClick={reset}>
          Try again
        </button>
      </section>
    </main>
  );
}
