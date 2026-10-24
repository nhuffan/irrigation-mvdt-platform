"use client";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { PanelSection } from "@/components/ui/panel-section";
import dynamic from "next/dynamic";
import { useState, useEffect, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { modelSelectionUrl } from "@/lib/model-deep-link";
import { Workspace } from "@/components/workspace";
import { getModelLinks } from "@/lib/api";
import type { ModelRecord, ModelAssetLink } from "@/types/media";
import { SourceInfo, VerificationBadge } from "@/components/asset/source-info";
const Viewer = dynamic(() => import("./cesium-viewer"), { ssr: false, loading: () => <div className="viewer-frame" role="status"><p className="viewer-status">Loading 3D viewer…</p></div> });
function ModelView({ model, initialObject, controls }: { model: ModelRecord; initialObject?: string; controls: ReactNode }) {
  const [links, setLinks] = useState<ModelAssetLink[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [settledAttempt, setSettledAttempt] = useState(-1);
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      void getModelLinks(model.id).then(value => { if (active) { setLinks(value); setError(false); setSettledAttempt(attempt); } }).catch(() => { if (active) { setLinks([]); setError(true); setSettledAttempt(attempt); } });
    });
    return () => { active = false; };
  }, [model.id, attempt]);
  const metadata = <>
    <VerificationBadge status={model.verification_status}/>
    <TechnicalMetadataPopover fields={{"Model UUID":model.id,"Model code":model.model_code,"Source UUID":model.source_id,Placement:model.coordinate_mode,Longitude:model.longitude,Latitude:model.latitude,Height:model.height,Heading:model.heading,Pitch:model.pitch,Roll:model.roll,Scale:model.scale}}/>
    <p className="summary-note">Placement and visibility do not establish surveyed accuracy or verified asset mapping.</p>
    <SourceInfo source={model.source}/>
  </>;
  if (!links) return <Workspace title="3D" panel={<PanelSection title="Model">{controls}<p role="status">Loading model asset links…</p></PanelSection>}><div className="viewer-frame" role="status"><p className="viewer-status">Preparing 3D viewer…</p></div></Workspace>;
  const mappingControls = <>{controls}{error && <div role="alert"><p>Asset mappings are unavailable. The model preview remains available; no missing mapping is inferred.</p><button className="text-link" disabled={settledAttempt !== attempt} onClick={() => setAttempt(n => n + 1)}>{settledAttempt !== attempt ? "Retrying asset mappings…" : "Retry asset mappings"}</button></div>}</>;
  return <Viewer key={model.id} model={model} links={links} initialObject={initialObject} modelControls={mappingControls} modelDetails={metadata}/>;
}
export function ModelBrowser({ models, initialModel, initialObject }: { models: ModelRecord[]; initialModel?: string; initialObject?: string }) {
  const params = useSearchParams();
  const requested = params.get("model") ?? initialModel;
  const id = models.find(m => m.id === requested)?.id ?? models[0]?.id;
  const object = params.has("model") || params.has("object") ? params.get("object") ?? undefined : initialObject;
  if (!models.length) return <section className="panel"><h2>3D models</h2><p className="muted">No 3D models are registered for this reservoir.</p></section>;
  const model = models.find(m => m.id === id)!;
  const controls = <label className="model-select">Active model<select value={id} onChange={event => window.history.pushState(null, "", modelSelectionUrl(window.location.href, event.target.value, null))}>{models.map(m => <option key={m.id} value={m.id}>{evidenceDisplayText(m.name)}</option>)}</select></label>;
  return <ModelView key={id} model={model} initialObject={object} controls={controls}/>;
}
