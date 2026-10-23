"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useSyncExternalStore, type ComponentProps } from "react";
import { documentHref } from "@/lib/document-navigation";

type Props = Omit<ComponentProps<typeof Link>, "href"> & { href: string };
const subscribeHash = (callback: () => void) => {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
};
const currentHash = () => window.location.hash;
const serverHash = () => "";

function ContextLink({ href, ...props }: Props) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const hash = useSyncExternalStore(subscribeHash, currentHash, serverHash);
  return <Link {...props} href={documentHref(href, `${pathname}${search ? `?${search}` : ""}${hash}`)} />;
}

/** Keep the origin in the URL for reloads, copied links and new tabs. */
export function DocumentLink(props: Props) {
  return <Suspense fallback={<Link {...props} />}><ContextLink {...props} /></Suspense>;
}
