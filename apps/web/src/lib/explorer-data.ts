import { getAssetTechnical, getAssetTimeline, getAssetCurrentCondition, getAssetDocuments, getAssetModelLinks } from "./api";
export async function getExplorerData(id: string) {
  const [technical, timeline, condition, documents, links] = await Promise.allSettled([
    getAssetTechnical(id), getAssetTimeline(id), getAssetCurrentCondition(id), getAssetDocuments(id), getAssetModelLinks(id),
  ]);
  return {
    technical: technical.status === "fulfilled" ? technical.value : null,
    events: timeline.status === "fulfilled" ? timeline.value.filter(e => e.verification_status === "VERIFIED") : null,
    condition: condition.status === "fulfilled" ? condition.value : null,
    conditionError: condition.status === "rejected",
    documents: documents.status === "fulfilled" ? documents.value : null,
    links: links.status === "fulfilled" ? links.value : null,
  };
}
export type ExplorerData = Awaited<ReturnType<typeof getExplorerData>>;
export type ExplorerRecords = Record<string, ExplorerData>;
