"use client";
export default function ErrorPage({ retry }: { retry: () => void }) {
  return (
    <main className="page-shell" role="alert">
      <h1>Unable to load 3D models</h1>
      <p>This does not mean no models exist.</p>
      <button onClick={retry}>Try again</button>
    </main>
  );
}
