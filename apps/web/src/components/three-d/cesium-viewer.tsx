"use client";
import { TechnicalMetadataPopover } from "@/components/asset/presentation";
import { useEffect, useRef, useState } from "react";
import type { Viewer, Model, ScreenSpaceEventHandler } from "cesium";
import type { ModelRecord, ModelAssetLink } from "@/types/media";
import { loadCesium } from "./cesium-loader";
import { selectedPrimitives } from "@/lib/model-selection";
import { pickedObjectKey } from "@/lib/model-picking";
import { AssetSidePanel } from "./asset-side-panel";
export default function CesiumViewer({
  model,
  links,
  initialObject,
}: {
  model: ModelRecord;
  links: ModelAssetLink[];
  initialObject?: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const selectionEffect = useRef<((key: string | null, focus?: boolean) => void) | null>(null);
  const selectedRef = useRef<string | null>(initialObject ?? null);
  const [highlighted, setHighlighted] = useState(false);
  const reset = useRef<(() => void) | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState<string | null>(
    initialObject ?? null,
  );
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    selectedRef.current = selected;
    selectionEffect.current?.(selected);
  }, [selected]);
  useEffect(() => {
    let disposed = false;
    let viewer: Viewer | undefined;
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
        const frame = () => {
          if (disposed || !loaded.ready) return;
          if (local) {
            v.camera.lookAtTransform(
              C.Matrix4.fromTranslation(loaded.boundingSphere.center),
              new C.HeadingPitchRange(
                C.Math.toRadians(25),
                C.Math.toRadians(-35),
                Math.max(loaded.boundingSphere.radius * 3, 20),
              ),
            );
          } else {
            v.camera.flyToBoundingSphere(loaded.boundingSphere, {
              duration: 0,
              offset: new C.HeadingPitchRange(
                C.Math.toRadians(25),
                C.Math.toRadians(-25),
                Math.max(loaded.boundingSphere.radius * 3, 20),
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
        const applySelection = (key: string | null, focus = false) => {
          if (!loaded.ready || disposed) return;
          const ids = selectedPrimitives(loaded, model.id, key);
          tint.selected = ids.length ? [{ pickIds: ids }] : [];
          selectionFrames = 3;
          setHighlighted(ids.length > 0);
          if (focus && ids.length) {
            const spheres = ids.map(p => p.object.detail?.primitive?.drawCommand?.boundingVolume).filter((b): b is import("cesium").BoundingSphere => !!b && Number.isFinite(b.radius) && b.radius > 0);
            if (spheres.length === ids.length) {
              const bounds = C.BoundingSphere.fromBoundingSpheres(spheres);
              v.camera.lookAtTransform(C.Matrix4.fromTranslation(bounds.center), new C.HeadingPitchRange(C.Math.toRadians(25), C.Math.toRadians(-50), Math.max(bounds.radius * 2.6, 1)));
            }
          }
          v.scene.requestRender();
        };
        // Streaming textures may rebuild draw commands and allocate fresh pick IDs.
        // Keep the selected-ID texture bound to the current primitive IDs, not stale colors.
        let lastIds: ReturnType<typeof selectedPrimitives> = [];
        v.scene.postRender.addEventListener(() => {
          if (disposed || !loaded.ready) return;
          const current = selectedPrimitives(loaded, model.id, selectedRef.current);
          if (current.length !== lastIds.length || current.some((id, i) => id !== lastIds[i])) {
            lastIds = current;
            applySelection(selectedRef.current);
          }
        });
        selectionEffect.current = applySelection;
        reset.current = frame;
        const ready = () => {
          if (!disposed) {
            clearTimeout(timer);
            setStatus("ready");
            frame();
            applySelection(selectedRef.current, true);
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
      disposed = true;
      clearTimeout(timer);
      reset.current = null;
      selectionEffect.current = null;
      if (handler && !handler.isDestroyed()) handler.destroy();
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
      else if (primitive && !primitive.isDestroyed()) primitive.destroy();
    };
  }, [model, attempt]);
  const link = links.find((item) => item.object_key === selected);
  return (
    <>
      {model.coordinate_mode === "LOCAL" && (
        <p className="muted">Local model preview · No geographic placement has been verified.</p>
      )}
      <div className="viewer-toolbar">
        <button onClick={() => reset.current?.()} disabled={status !== "ready"}>
          Reset camera
        </button>
        <button onClick={() => selectionEffect.current?.(selected, true)} disabled={!highlighted}>Focus selected object</button>
        <button onClick={() => setSelected(null)}>Clear selection</button>
        <span className="muted">
          Drag to rotate/pan · Wheel to zoom · Click an object
        </span>
      </div>
      <p className="selection-feedback" role="status">{selected ? highlighted ? "Selected mesh highlighted · amber tint · original materials preserved" : "Selection has no reliable mesh identifier; visual highlight unavailable." : "No object selected"}</p>
      <div className="three-d-grid">
        <div className="viewer-frame">
          <div ref={container} className="cesium-container" />
          {status === "loading" && (
            <p className="viewer-status" role="status">
              Loading 3D model…
            </p>
          )}
          {status === "error" && (
            <div className="viewer-status" role="alert">
              <p>{message}</p>
              <button onClick={() => setAttempt((n) => n + 1)}>
                Try again
              </button>
            </div>
          )}
        </div>
        {link ? (
          <AssetSidePanel key={link.id} link={link} placement={model.coordinate_mode} />
        ) : (
          <aside className="panel">
            <h2>Asset selection</h2>
            <p className="muted mt-3">
              {selected
                ? "No asset is linked to this object."
                : "Select a model object to view its asset information."}
            </p><TechnicalMetadataPopover fields={{"Object key":selected}}/>
          </aside>
        )}
      </div>
      <details className="source-info mt-4">
        <summary>Linked objects · keyboard navigation</summary>
        <ul className="object-list">
          {links.map((item) => (
            <li key={item.id}>
              <button onClick={() => setSelected(item.object_key)}>
                Representative object
              </button>
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}
