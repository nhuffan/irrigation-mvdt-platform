"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="page-shell" role="alert">
      <h1>Unable to load 3D models</h1>
      <p>This does not mean no models exist.</p>
      <button onClick={reset}>Try again</button>
    </main>
  );
}
