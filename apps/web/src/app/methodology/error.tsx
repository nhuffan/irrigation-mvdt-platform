"use client";
export default function ErrorPage({ retry }: { retry: () => void }) {
  return <main className="page-shell"><h1>Research summary unavailable</h1><p>The data API or controlled summary could not be read. Coverage has not been replaced with zero.</p><button className="button button-secondary" onClick={retry}>Retry</button></main>;
}
