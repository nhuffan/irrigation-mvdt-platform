"use client";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import dynamic from "next/dynamic";
import { useState, useEffect } from "react";
import { getModelLinks } from "@/lib/api";
import type { ModelRecord, ModelAssetLink } from "@/types/media";
import { SourceInfo, VerificationBadge } from "@/components/asset/source-info";
const Viewer = dynamic(() => import("./cesium-viewer"), {
  ssr: false,
  loading: () => <p role="status">Loading 3D viewer…</p>,
});
function ModelView({
  model,
  initialObject,
}: {
  model: ModelRecord;
  initialObject?: string;
}) {
  const [links, setLinks] = useState<ModelAssetLink[] | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    void getModelLinks(model.id)
      .then((value) => {
        if (active) {
          setLinks(value);
          setError(false);
        }
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [model.id, attempt]);
  return (
    <>
      <details className="model-metadata"><summary>Model metadata · {model.coordinate_mode} · {model.verification_status}</summary>
        <h2>{evidenceDisplayText(model.name)}</h2>
        <VerificationBadge status={model.verification_status} />
        <p className="muted mt-3">
          {model.coordinate_mode} · {model.format} · {model.model_type}
        </p>
        <TechnicalMetadataPopover fields={{"Model UUID":model.id,"Model code":model.model_code,"Source UUID":model.source_id,Placement:model.coordinate_mode,Longitude:model.longitude,Latitude:model.latitude,Height:model.height,Heading:model.heading,Pitch:model.pitch,Roll:model.roll,Scale:model.scale}}/>
        <p className="muted text-sm">
          Placement and visibility do not establish surveyed accuracy or
          verified asset mapping.
        </p>
        <SourceInfo source={model.source} />
      </details>
      {error ? (
        <div role="alert" className="panel">
          Unable to load model asset links.{" "}
          <button onClick={() => setAttempt((n) => n + 1)}>Try again</button>
        </div>
      ) : links ? (
        <Viewer key={`${model.id}:${initialObject ?? ""}`} model={model} links={links} initialObject={initialObject} />
      ) : (
        <p role="status">Loading model asset links…</p>
      )}
    </>
  );
}
export function ModelBrowser({
  models,
  initialModel,
  initialObject,
}: {
  models: ModelRecord[];
  initialModel?: string;
  initialObject?: string;
}) {
  const [id, setId] = useState(
    models.find((m) => m.id === initialModel)?.id ?? models.find(m => m.model_code.startsWith("RS-"))?.id ?? models[0]?.id,
  );
  if (!models.length)
    return (
      <section className="panel mt-6">
        <h2>3D models</h2>
        <p className="muted">No 3D models are registered for this reservoir.</p>
      </section>
    );
  const model = models.find((m) => m.id === id)!;
  return (
    <>
      <label className="model-select">
        Model{" "}
        <select value={id} onChange={(event) => setId(event.target.value)}>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {evidenceDisplayText(m.name)}
            </option>
          ))}
        </select>
      </label>
      <ModelView
        key={id}
        model={model}
        initialObject={id === initialModel ? initialObject : undefined}
      />
    </>
  );
}
