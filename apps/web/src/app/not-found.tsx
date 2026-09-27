import Link from "next/link";
export default function NotFound() {
  return (
    <main className="page-shell">
      <p className="eyebrow">404 · Not found</p>
      <h1>Reservoir or page not found</h1>
      <p className="muted my-5">
        This address does not match an available record or page.
      </p>
      <Link className="button" href="/">
        Back to registry
      </Link>
    </main>
  );
}
