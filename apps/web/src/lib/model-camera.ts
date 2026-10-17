// Fit to the limiting field of view so narrow viewports do not clip the target.
export function cameraFitDistance(radius: number, verticalFov: number, aspect: number, padding = 1.12) {
  const r = Number.isFinite(radius) && radius > 0 ? radius : 1;
  const fov = Number.isFinite(verticalFov) && verticalFov > 0 && verticalFov < Math.PI ? verticalFov : Math.PI / 3;
  const ratio = Number.isFinite(aspect) && aspect > 0 ? aspect : 1;
  const angle = Math.min(fov / 2, Math.atan(Math.tan(fov / 2) * ratio));
  return Math.max(r * Math.max(padding, 1) / Math.sin(angle), 1);
}
export function initialCameraObject(initialObject: string | undefined, coordinateMode: string, links: Array<{ object_key: string }>) {
  if (initialObject) return initialObject;
  return coordinateMode === "LOCAL" && links.length === 1 ? links[0].object_key : null;
}
