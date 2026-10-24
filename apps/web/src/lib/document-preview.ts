/** Original links always retain physical numbering, independent of embedded rendering. */
export function originalDocumentUrl(id: string, page = 1): string {
  return `/api/media/documents/${encodeURIComponent(id)}#page=${Number.isSafeInteger(page) && page > 0 ? page : 1}`;
}

export function documentMediaError(status: number): string {
  return status === 410 ? "The original file is unavailable; its metadata is retained."
    : status === 404 ? "The original could not be found. Check its source details."
    : "The original could not be loaded. Check the connection and retry.";
}
