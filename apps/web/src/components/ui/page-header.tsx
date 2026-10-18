import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description }: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
}) {
  return <header className="tab-page-header">
    <p className="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    {description && <p className="muted">{description}</p>}
  </header>;
}
