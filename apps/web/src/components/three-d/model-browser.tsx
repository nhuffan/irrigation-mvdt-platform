"use client";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { PanelSection } from "@/components/ui/panel-section";
import dynamic from "next/dynamic";
import { useState, useEffect, type ReactNode } from "react";
import { getModelLinks } from "@/lib/api";
import type { ModelRecord, ModelAssetLink } from "@/types/media";
import { SourceInfo, VerificationBadge } from "@/components/asset/source-info";
const Viewer = dynamic(() => import("./cesium-viewer"), { ssr: false, loading: () => <p role="status">Loading 3D viewer…</p> });
function ModelView({ model, initialObject, controls }: { model: ModelRecord; initialObject?: string; controls: ReactNode }) {
  const [links, setLinks] = useState<ModelAssetLink[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void getModelLinks(model.id).then(value => { if (active) { setLinks(value); setError(false); } }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [model.id, attempt]);
  const metadata = <>
    <VerificationBadge status={model.verification_status}/>
    <TechnicalMetadataPopover fields={{"Model UUID":model.id,"Model code":model.model_code,"Source UUID":model.source_id,Placement:model.coordinate_mode,Longitude:model.longitude,Latitude:model.latitude,Height:model.height,Heading:model.heading,Pitch:model.pitch,Roll:model.roll,Scale:model.scale}}/>
    <p className="summary-note">Placement and visibility do not establish surveyed accuracy or verified asset mapping.</p>
    <SourceInfo source={model.source}/>
  </>;
  if (error) return <PanelSection title="Model unavailable">{controls}<p role="alert">Unable to load model asset links.</p><button className="button compact-button" onClick={() => setAttempt(n => n + 1)}>Try again</button></PanelSection>;
  if (!links) return <PanelSection title="Model">{controls}<p role="status">Loading model asset links…</p></PanelSection>;
  return <Viewer key={`${model.id}:${initialObject ?? ""}`} model={model} links={links} initialObject={initialObject} modelControls={controls} modelDetails={metadata}/>;
}
export function ModelBrowser({ models, initialModel, initialObject }: { models: ModelRecord[]; initialModel?: string; initialObject?: string }) {
  const [id, setId] = useState(models.find(m => m.id === initialModel)?.id ?? models[0]?.id);
  if (!models.length) return <section className="panel"><h2>3D models</h2><p className="muted">No 3D models are registered for this reservoir.</p></section>;
  const model = models.find(m => m.id === id)!;
  const controls = <label className="model-select">Active model<select value={id} onChange={event => setId(event.target.value)}>{models.map(m => <option key={m.id} value={m.id}>{evidenceDisplayText(m.name)}</option>)}</select></label>;
  return <ModelView key={id} model={model} initialObject={id === initialModel ? initialObject : undefined} controls={controls}/>;
}
