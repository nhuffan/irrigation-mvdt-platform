import { assetSymbol } from "@/lib/asset-symbol";
export function AssetSymbol({ category }: { category: string }) {
  return <svg className="asset-category-symbol" viewBox="0 0 24 24" aria-hidden="true"><path d={assetSymbol(category).path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
