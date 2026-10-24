"use client";
import { cameraFitDistance, initialCameraObject } from "@/lib/model-camera";
import { PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { Workspace } from "@/components/workspace";
import { observeCanvasResize } from "@/lib/workspace-layout";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { useEffect, useEffectEvent, useRef, useState, type ReactNode } from "react";
import type { Viewer, Model, ScreenSpaceEventHandler } from "cesium";
import type { ModelRecord, ModelAssetLink } from "@/types/media";
import { loadCesium } from "./cesium-loader";
import { modelSelectionUrl, uniqueObjectLink } from "@/lib/model-deep-link";
import { selectedPrimitives } from "@/lib/model-selection";
import { pickedObjectKey } from "@/lib/model-picking";
import { cameraView, readView, saveView, viewStorage } from "@/lib/workspace-view-state";
import { AssetSidePanel } from "./asset-side-panel";
export default function CesiumViewer({
  model,
  links,
  initialObject, modelControls, modelDetails,
}: {
  model: ModelRecord;
  links: ModelAssetLink[];
  initialObject?: string;
  modelControls?: ReactNode;
  modelDetails?: ReactNode;
}) {
  const [defaultObject] = useState(() => initialCameraObject(initialObject, model.coordinate_mode, links));
  const lastObject = useRef(initialObject);
  const container = useRef<HTMLDivElement>(null);
  const selectionEffect = useRef<((key: string | null, focus?: boolean) => void) | null>(null);
  const selectedRef = useRef<string | null>(defaultObject);
  const [highlighted, setHighlighted] = useState(false);
  const showAll = useRef<(() => void) | null>(null);
  const reset = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<string | null>(
    defaultObject,
  );
  const [attempt, setAttempt] = useState(0);
  const restoreObject = useEffectEvent((object?: string) => setSelected(object ?? null));
  useEffect(() => {
    if (lastObject.current !== initialObject) { lastObject.current = initialObject; restoreObject(initialObject); }
  }, [initialObject]);

  useEffect(() => {
    window.history.replaceState(null, "", modelSelectionUrl(window.location.href, model.id, selected));
    selectedRef.current = selected;
    selectionEffect.current?.(selected);
  }, [selected, model.id]);
  useEffect(() => {
    let disposed = false;
    let viewer: Viewer | undefined;
    let stopCameraEvents: (() => void) | undefined;
    let saveCamera: (() => void) | undefined;
    let stopRemembering: (() => void) | undefined;
    let stopResize: (() => void) | undefined;
    let primitive: Model | undefined;
    let handler: ScreenSpaceEventHandler | undefined;
    const timer = setTimeout(() => {
      if (!disposed) {
        setStatus("error");
        setMessage(
          "3D loading timed out. Check file availability and WebGL support.",
        );
      }
    }, 30000);
    async function start() {
      setStatus("loading");
      setMessage("");
      try {
        if (model.format !== "GLB")
          throw new Error(
            "This viewer supports self-contained GLB models. This format is not supported yet.",
          );
        const local = model.coordinate_mode === "LOCAL";
        if (
          !local &&
          (model.longitude === null ||
            model.latitude === null ||
            model.height === null)
        )
          throw new Error("Model placement is incomplete.");
        const C = await loadCesium();
        if (disposed || !container.current) return;
        const v = new C.Viewer(container.current, {
          baseLayer: false,
          ...(local ? { globe: false as const } : {}),
          baseLayerPicker: false,
          geocoder: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          animation: false,
          timeline: false,
          fullscreenButton: false,
          selectionIndicator: false,
          infoBox: false,
          skyBox: false,
          skyAtmosphere: false,
          requestRenderMode: true,
        });
        viewer = v;
        stopResize = observeCanvasResize(container.current, () => { v.resize(); v.scene.requestRender(); });
        if (v.scene.globe) {
          v.scene.globe.baseColor = C.Color.fromCssColorString("#263c48");
        }
        if (local) {
          v.scene.backgroundColor = C.Color.fromCssColorString("#263c48");
          if (v.scene.sun) v.scene.sun.show = false;
          if (v.scene.moon) v.scene.moon.show = false;
          v.scene.screenSpaceCameraController.enableCollisionDetection = false;
          v.scene.light = new C.DirectionalLight({
            direction: new C.Cartesian3(-0.3, -0.5, -1),
            intensity: 2,
          });
        }
        v.scene.renderError.addEventListener(() => {
          if (!disposed) {
            clearTimeout(timer);
            setStatus("error");
            setMessage("Unable to render 3D. WebGL may be unavailable.");
          }
        });
        const rotation = new C.HeadingPitchRoll(
          C.Math.toRadians(model.heading),
          C.Math.toRadians(model.pitch),
          C.Math.toRadians(model.roll),
        );
        const matrix = local
          ? C.Matrix4.fromRotationTranslation(
              C.Matrix3.fromQuaternion(
                C.Quaternion.fromHeadingPitchRoll(rotation),
              ),
            )
          : C.Transforms.headingPitchRollToFixedFrame(
              C.Cartesian3.fromDegrees(
                model.longitude!, model.latitude!, model.height!,
              ),
              rotation,
            );
        const loaded = await C.Model.fromGltfAsync({
          url: `/api/media/models/${model.id}`,
          modelMatrix: matrix,
          scale: model.scale,
          id: model.id,
          allowPicking: true,
        });
        if (disposed) {
          loaded.destroy();
          return;
        }
        primitive = loaded;
        v.scene.primitives.add(loaded);
        const distance = (radius: number) => {
          const frustum = v.camera.frustum;
          const verticalFov = frustum instanceof C.PerspectiveFrustum ? frustum.fovy ?? Math.PI / 3 : Math.PI / 3;
          return cameraFitDistance(radius, verticalFov, v.scene.canvas.clientWidth / Math.max(v.scene.canvas.clientHeight, 1));
        };
        const frame = () => {
          if (disposed || !loaded.ready) return;
          if (local) {
            v.camera.lookAtTransform(
              C.Matrix4.fromTranslation(loaded.boundingSphere.center),
              new C.HeadingPitchRange(
                C.Math.toRadians(25),
                C.Math.toRadians(-35),
                distance(loaded.boundingSphere.radius),
              ),
            );
          } else {
            v.camera.flyToBoundingSphere(loaded.boundingSphere, {
              duration: 0,
              offset: new C.HeadingPitchRange(
                C.Math.toRadians(25),
                C.Math.toRadians(-25),
                distance(loaded.boundingSphere.radius),
              ),
            });
          }
          v.scene.requestRender();
        };
        const tint = v.scene.postProcessStages.add(new C.PostProcessStage({
          name: `object-selection-${model.id}`,
          fragmentShader: `uniform sampler2D colorTexture;
            in vec2 v_textureCoordinates;
            void main() {
              vec4 color = texture(colorTexture, v_textureCoordinates);
              out_FragColor = czm_selected() ? vec4(mix(color.rgb, vec3(1.0, 0.68, 0.08), 0.6), color.a) : color;
            }`,
        }));
        tint.selected = [];
        // Render again after selected-ID texture/shader preparation in request-render mode.
        let selectionFrames = 0;
        v.scene.postRender.addEventListener(() => {
          if (selectionFrames > 0) { selectionFrames--; v.scene.requestRender(); }
        });
        const focusObject = (key: string | null) => {
          const ids = selectedPrimitives(loaded, model.id, key);
          if (!ids.length) return false;
          const spheres = ids.map(p => p.object.detail?.primitive?.drawCommand?.boundingVolume).filter((b): b is import("cesium").BoundingSphere => !!b && Number.isFinite(b.radius) && b.radius > 0);
          if (spheres.length !== ids.length) return false;
          const bounds = C.BoundingSphere.fromBoundingSpheres(spheres);
          v.camera.lookAtTransform(C.Matrix4.fromTranslation(bounds.center), new C.HeadingPitchRange(C.Math.toRadians(25), C.Math.toRadians(-35), distance(bounds.radius)));
          v.scene.requestRender();
          return true;
        };
        const applySelection = (key: string | null, focus = false) => {
          if (!loaded.ready || disposed) return;
          const ids = selectedPrimitives(loaded, model.id, key);
          tint.selected = ids.length ? [{ pickIds: ids }] : [];
          selectionFrames = 3;
          setHighlighted(ids.length > 0);
          if (focus) focusObject(key);
          v.scene.requestRender();
        };
        // Pick volumes may become available after readyEvent. Focus once, never chase the user's camera.
        let initialFocusFrames = defaultObject ? 60 : 0;
        const cancelInitialFocus = () => { initialFocusFrames = 0; };
        v.scene.canvas.addEventListener("pointerdown", cancelInitialFocus);
        v.scene.canvas.addEventListener("wheel", cancelInitialFocus, { passive: true });
        stopCameraEvents = () => {
          v.scene.canvas.removeEventListener("pointerdown", cancelInitialFocus);
          v.scene.canvas.removeEventListener("wheel", cancelInitialFocus);
        };
        // Streaming textures may rebuild draw commands and allocate fresh pick IDs.
        // Keep the selected-ID texture bound to the current primitive IDs, not stale colors.
        let lastIds: ReturnType<typeof selectedPrimitives> = [];
        v.scene.postRender.addEventListener(() => {
          if (disposed || !loaded.ready) return;
          if (initialFocusFrames > 0) {
            initialFocusFrames--;
            if (focusObject(selectedRef.current)) initialFocusFrames = 0;
            else v.scene.requestRender();
          }
          const current = selectedPrimitives(loaded, model.id, selectedRef.current);
          if (current.length !== lastIds.length || current.some((id, i) => id !== lastIds[i])) {
            lastIds = current;
            applySelection(selectedRef.current);
          }
        });
        selectionEffect.current = applySelection;
        showAll.current = () => { initialFocusFrames = 0; frame(); };
        reset.current = () => {
          initialFocusFrames = 0;
          if (!focusObject(selectedRef.current ?? defaultObject)) frame();
        };
        const cameraKey = () => `3d:${JSON.stringify([model.id, model.coordinate_mode, model.longitude, model.latitude, model.height, model.heading, model.pitch, model.roll, model.scale, selectedRef.current])}`;
        saveCamera = () => {
          if (disposed || !loaded.ready || v.isDestroyed()) return;
          const array = (vector: import("cesium").Cartesian3) => [vector.x, vector.y, vector.z];
          saveView(viewStorage(), cameraKey(), { position: array(v.camera.positionWC), direction: array(v.camera.directionWC), up: array(v.camera.upWC) });
        };
        stopRemembering = v.camera.moveEnd.addEventListener(saveCamera);
        const ready = () => {
          if (!disposed) {
            clearTimeout(timer);
            setStatus("ready");
            const remembered = readView(viewStorage(), cameraKey(), cameraView);
            frame();
            applySelection(selectedRef.current, true);
            if (remembered) {
              initialFocusFrames = 0;
              v.camera.lookAtTransform(C.Matrix4.IDENTITY);
              v.camera.setView({ destination: C.Cartesian3.fromArray(remembered.position), orientation: { direction: C.Cartesian3.fromArray(remembered.direction), up: C.Cartesian3.fromArray(remembered.up) } });
              v.scene.requestRender();
            }
          }
        };
        if (loaded.ready) ready();
        else loaded.readyEvent.addEventListener(ready);
        loaded.errorEvent.addEventListener(() => {
          if (!disposed) {
            clearTimeout(timer);
            setStatus("error");
            setMessage("Unable to load model resources.");
          }
        });
        handler = new C.ScreenSpaceEventHandler(v.scene.canvas);
        handler.setInputAction(
          (event: { position: import("cesium").Cartesian2 }) => {
            setSelected(
              pickedObjectKey(v.scene.pick(event.position), model.id),
            );
          },
          C.ScreenSpaceEventType.LEFT_CLICK,
        );
        v.scene.requestRender();
      } catch (error) {
        if (!disposed) {
          clearTimeout(timer);
          setStatus("error");
          setMessage(
            error instanceof Error ? error.message : "Unable to load 3D model.",
          );
        }
      }
    }
    void start();
    return () => {
      saveCamera?.();
      stopRemembering?.();
      disposed = true;
      clearTimeout(timer);
      reset.current = null;
      showAll.current = null;
      stopCameraEvents?.();
      selectionEffect.current = null;
      if (handler && !handler.isDestroyed()) handler.destroy();
      stopResize?.();
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      else if (primitive && !primitive.isDestroyed()) primitive.destroy();
    };
  }, [model, attempt, defaultObject]);
  const link = uniqueObjectLink(links, selected);
  return (
    <Workspace title="3D" panel={<>
      <PanelSection title="Model" description="Local reference & representation">
        {modelControls}
        <div className="context-badges"><span className="presentation-badge">{model.coordinate_mode}</span><span className="presentation-badge">{model.format}</span><span className="presentation-badge">Representative model</span></div>
      </PanelSection>
      <PanelSection title="View controls" description="Drag to orbit · Scroll to zoom">
        <div className="view-control-grid">
          <button onClick={() => reset.current?.()} disabled={status !== "ready"}>Reset view</button>
          <button onClick={() => showAll.current?.()} disabled={status !== "ready"}>Entire model</button>
          <button onClick={() => selectionEffect.current?.(selected, true)} disabled={!highlighted}>Focus selected</button>
          <button onClick={() => setSelected(null)} disabled={!selected}>Clear selection</button>
        </div>
      </PanelSection>
      {link ? <AssetSidePanel key={link.id} link={link} placement={model.coordinate_mode}/> : <PanelSection title="Selected object">
        <p className="empty-state">{selected ? "No unique asset mapping is established for this object; identity is missing or ambiguous." : "Select a model object to view its asset information."}</p>
        <TechnicalMetadataPopover fields={{"Object key":selected}}/>
      </PanelSection>}
      <PanelDisclosure title={`Linked objects · ${links.length}`}>
        <ul className="object-list">{links.map(item => <li key={item.id}><button onClick={() => { setSelected(item.object_key); selectionEffect.current?.(item.object_key, true); }}>{evidenceDisplayText(item.object_name ?? item.object_key)}</button></li>)}</ul>
      </PanelDisclosure>
      <PanelDisclosure title="Model source & limitations">
        <p className="summary-note">{model.coordinate_mode === "LOCAL" ? "Local preview only. Geographic placement is unverified." : "Placement follows stored model parameters."} Representative links do not establish a specific child building identity.</p>
        {modelDetails}
      </PanelDisclosure>
    </>}>
      <div className="viewport-heading"><h2>Model viewport</h2><span>{model.coordinate_mode} · {status === "ready" ? "Ready" : status === "error" ? "Unavailable" : "Loading"}</span></div>
      <div className="viewer-frame">
        <div ref={container} className="cesium-container"/>
        {status === "loading" && <p className="viewer-status" role="status">Loading 3D model…</p>}
        {status === "error" && <div className="viewer-status" role="alert"><p>{message}</p><button onClick={() => setAttempt(n => n + 1)}>Try again</button></div>}
      </div>
      <p className="selection-feedback" role="status">{selected ? highlighted ? "Object selected · amber highlight" : "Object identifier selected · mesh highlight unavailable" : "No object selected"}</p>
    </Workspace>
  );
}
