"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useSyncExternalStore, type ComponentProps } from "react";
import { documentHref } from "@/lib/document-navigation";

type Props = Omit<ComponentProps<typeof Link>, "href"> & { href: string; returnAnchor?: string };
const subscribeHash = (callback: () => void) => {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
};
const currentHash = () => window.location.hash;
const serverHash = () => "";

function ContextLink({ href, returnAnchor, ...props }: Props) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const hash = useSyncExternalStore(subscribeHash, currentHash, serverHash);
  return <Link {...props} href={documentHref(href, `${pathname}${search ? `?${search}` : ""}${returnAnchor ? `#${encodeURIComponent(returnAnchor)}` : hash}`)} />;
}

/** Shared origin-aware drilldown for assets, sources, documents and workspaces. */
export function OriginLink({ returnAnchor, ...props }: Props) {
  return <Suspense fallback={<Link {...props} />}><ContextLink {...props} returnAnchor={returnAnchor} /></Suspense>;
}

/** Existing document callers share the same safe navigation contract. */
export const DocumentLink = OriginLink;
