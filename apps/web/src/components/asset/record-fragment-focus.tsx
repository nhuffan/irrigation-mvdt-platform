"use client";

import { useEffect } from "react";
import { observeRecordFragment } from "@/lib/record-fragment-focus";

export function RecordFragmentFocus({ recordIds }: { recordIds: string[] }) {
  useEffect(() => observeRecordFragment(recordIds), [recordIds]);
  return null;
}
